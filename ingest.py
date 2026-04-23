"""
Document ingestion pipeline — optimised for large document sets (1000+ files).

Features:
  - Batch embedding to avoid memory overflow
  - Manifest file: tracks ingested files so you can resume if interrupted
  - Skips already-ingested files by default (use --force to re-ingest all)
  - tqdm progress bars in CLI mode
  - Supports PDF and DOCX

Usage (CLI):
  python ingest.py                          # ingest from data/raw/
  python ingest.py --folder C:/my/docs      # ingest from custom folder
  python ingest.py --force                  # re-ingest everything
  python ingest.py --batch-size 50          # embed 50 chunks at a time (lower = less RAM)

Called from app.py for single-file UI uploads via ingest_file().
"""
import json
import sys
from pathlib import Path
from typing import List

from config import (
    RAW_DOCS_DIR, FAISS_INDEX_DIR, DATA_DIR,
    EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP,
)
from utils.loader import load_pdfs, load_docx
from utils.chunker import chunk_documents
from utils.logger import get_logger

log = get_logger(__name__)

# Manifest file — records which files have already been ingested
MANIFEST_PATH = DATA_DIR / "ingested_manifest.json"

# How many chunks to embed in one go (tune down if you hit RAM limits)
DEFAULT_BATCH_SIZE = 100


# ── Embeddings ─────────────────────────────────────────────────────────────

def _get_embeddings():
    """HuggingFace sentence-transformers — local, free, no API key."""
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


# ── Manifest helpers ────────────────────────────────────────────────────────

def _load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def _save_manifest(manifest: dict):
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _is_ingested(file_path: Path, manifest: dict) -> bool:
    key = str(file_path.resolve())
    stat = file_path.stat()
    entry = manifest.get(key)
    if not entry:
        return False
    # Re-ingest if file was modified since last ingest
    return entry.get("mtime") == stat.st_mtime and entry.get("size") == stat.st_size


def _mark_ingested(file_path: Path, chunks: int, manifest: dict):
    stat = file_path.stat()
    manifest[str(file_path.resolve())] = {
        "name":   file_path.name,
        "chunks": chunks,
        "mtime":  stat.st_mtime,
        "size":   stat.st_size,
    }


# ── Index helpers ───────────────────────────────────────────────────────────

def index_exists() -> bool:
    return (FAISS_INDEX_DIR / "index.faiss").exists()


def _upsert_chunks(chunks: list, embeddings, batch_size: int):
    """Embed chunks in batches and upsert into the FAISS index."""
    from langchain_community.vectorstores import FAISS

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i: i + batch_size]
        if index_exists():
            vs = FAISS.load_local(
                str(FAISS_INDEX_DIR), embeddings,
                allow_dangerous_deserialization=True,
            )
            vs.add_documents(batch)
        else:
            vs = FAISS.from_documents(batch, embeddings)
        vs.save_local(str(FAISS_INDEX_DIR))
        log.debug(f"  Batch {i // batch_size + 1}: saved {len(batch)} chunks")


# ── Single-file ingest (used by UI upload) ──────────────────────────────────

def ingest_file(file_path: Path) -> int:
    """
    Ingest a single PDF or DOCX file into the FAISS index.
    Called from app.py when a user uploads a file via the UI.
    """
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        all_docs = load_pdfs(file_path.parent)
    elif ext == ".docx":
        all_docs = load_docx(file_path.parent)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    docs = [d for d in all_docs if d.metadata.get("source_file") == file_path.name]
    if not docs:
        log.warning(f"No content extracted from {file_path.name}")
        return 0

    chunks     = chunk_documents(docs, CHUNK_SIZE, CHUNK_OVERLAP)
    embeddings = _get_embeddings()
    _upsert_chunks(chunks, embeddings, DEFAULT_BATCH_SIZE)

    # Update manifest
    manifest = _load_manifest()
    _mark_ingested(file_path, len(chunks), manifest)
    _save_manifest(manifest)

    log.info(f"Ingested '{file_path.name}' → {len(chunks)} chunks")
    return len(chunks)


# ── Bulk folder ingest (CLI + can be called programmatically) ───────────────

def ingest_folder(
    folder: Path = RAW_DOCS_DIR,
    force: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE,
    show_progress: bool = False,
) -> dict:
    """
    Ingest all PDFs and DOCX files from a folder into the FAISS index.

    Parameters
    ----------
    folder        : Folder to scan (recursive)
    force         : If True, re-ingest even already-ingested files
    batch_size    : Chunks per embedding batch (lower = less RAM usage)
    show_progress : Show tqdm progress bar (CLI mode)

    Returns dict with ingestion stats.
    """
    manifest   = _load_manifest()
    embeddings = _get_embeddings()

    # Collect all files
    all_files = (
        list(folder.glob("**/*.pdf")) +
        list(folder.glob("**/*.docx"))
    )

    if not all_files:
        log.warning(f"No PDF or DOCX files found in: {folder}")
        return {"total": 0, "ingested": 0, "skipped": 0, "failed": 0, "chunks": 0}

    log.info(f"Found {len(all_files)} file(s) in {folder}")

    stats = {"total": len(all_files), "ingested": 0, "skipped": 0, "failed": 0, "chunks": 0}

    # Progress iterator
    iterator = all_files
    if show_progress:
        try:
            from tqdm import tqdm
            iterator = tqdm(all_files, desc="Ingesting", unit="file", ncols=80)
        except ImportError:
            pass

    for file_path in iterator:
        # Skip already-ingested unless --force
        if not force and _is_ingested(file_path, manifest):
            log.debug(f"  SKIP (already ingested): {file_path.name}")
            stats["skipped"] += 1
            if show_progress and hasattr(iterator, "set_postfix"):
                iterator.set_postfix(skip=stats["skipped"], done=stats["ingested"])
            continue

        try:
            # Load just this specific file directly
            ext = file_path.suffix.lower()
            if ext == ".pdf":
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(str(file_path))
                docs = loader.load()
                for d in docs:
                    d.metadata["source_file"] = file_path.name
                    d.metadata["file_type"] = "pdf"
            elif ext == ".docx":
                from langchain_community.document_loaders import Docx2txtLoader
                loader = Docx2txtLoader(str(file_path))
                docs = loader.load()
                for d in docs:
                    d.metadata["source_file"] = file_path.name
                    d.metadata["file_type"] = "docx"
            else:
                stats["skipped"] += 1
                continue

            if not docs:
                log.warning(f"  No content: {file_path.name}")
                stats["skipped"] += 1
                continue

            # Chunk + embed + save
            chunks = chunk_documents(docs, CHUNK_SIZE, CHUNK_OVERLAP)
            _upsert_chunks(chunks, embeddings, batch_size)

            # Mark as done
            _mark_ingested(file_path, len(chunks), manifest)
            _save_manifest(manifest)

            stats["ingested"] += 1
            stats["chunks"]   += len(chunks)
            log.info(f"  OK: {file_path.name} ({len(chunks)} chunks)")

        except Exception as e:
            log.error(f"  ❌ FAILED: {file_path.name} — {e}")
            stats["failed"] += 1

        if show_progress and hasattr(iterator, "set_postfix"):
            iterator.set_postfix(
                done=stats["ingested"],
                skip=stats["skipped"],
                fail=stats["failed"],
            )

    return stats


# ── Manifest inspection helpers ─────────────────────────────────────────────

def get_ingested_file_list() -> list:
    """Return list of already-ingested file names (for UI display)."""
    manifest = _load_manifest()
    return [v["name"] for v in manifest.values()]


def reset_manifest():
    """Clear the manifest so all files will be re-ingested on next run."""
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()
    log.info("Manifest reset. All files will be re-ingested on next run.")


# ── CLI entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="PayGlobal bulk document ingestion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingest.py
  python ingest.py --folder "C:/PayGlobal Docs"
  python ingest.py --force
  python ingest.py --batch-size 30
  python ingest.py --status
        """,
    )
    parser.add_argument(
        "--folder", default=str(RAW_DOCS_DIR),
        help=f"Folder containing PDFs/DOCX (default: {RAW_DOCS_DIR})"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-ingest all files even if already done"
    )
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
        help=f"Chunks per embedding batch (default: {DEFAULT_BATCH_SIZE}). Lower = less RAM."
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show which files have already been ingested, then exit"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Clear the manifest (force full re-ingest on next run)"
    )
    args = parser.parse_args()

    # ── Status mode ──
    if args.status:
        manifest = _load_manifest()
        if not manifest:
            print("No files ingested yet.")
        else:
            total_chunks = sum(v.get("chunks", 0) for v in manifest.values())
            print(f"\n{'File':<60} {'Chunks':>8}")
            print("-" * 70)
            for entry in manifest.values():
                print(f"  {entry['name']:<58} {entry.get('chunks', '?'):>8}")
            print("-" * 70)
            print(f"  {'TOTAL: ' + str(len(manifest)) + ' files':<58} {total_chunks:>8} chunks\n")
        sys.exit(0)

    # ── Reset mode ──
    if args.reset:
        reset_manifest()
        print("✅ Manifest cleared. Run ingestion again to re-index everything.")
        sys.exit(0)

    # ── Ingest mode ──
    folder = Path(args.folder)
    if not folder.exists():
        print(f"❌ Folder not found: {folder}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  PayGlobal Bulk Ingestion")
    print(f"  Folder     : {folder}")
    print(f"  Force      : {args.force}")
    print(f"  Batch size : {args.batch_size} chunks")
    print(f"{'='*60}\n")

    stats = ingest_folder(
        folder=folder,
        force=args.force,
        batch_size=args.batch_size,
        show_progress=True,
    )

    print(f"\n{'='*60}")
    print(f"  INGESTION COMPLETE")
    print(f"  Total files  : {stats['total']}")
    print(f"  Ingested     : {stats['ingested']}")
    print(f"  Skipped      : {stats['skipped']} (already done)")
    print(f"  Failed       : {stats['failed']}")
    print(f"  Total chunks : {stats['chunks']}")
    print(f"{'='*60}\n")

    if stats["failed"] > 0:
        print("⚠️  Some files failed. Check data/logs/payglobal_bot.log for details.")
