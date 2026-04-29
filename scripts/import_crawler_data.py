import argparse
import json
import shutil
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import config and ingest modules
sys.path.append(str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document

from config import FAISS_INDEX_DIR
import ingest
from utils.logger import get_logger

# Force allow deserialization during our script execution so FAISS can reload the index between batches
ingest.ALLOW_DANGEROUS_DESERIALIZATION = True

log = get_logger(__name__)

def import_jsonl(jsonl_path: str, clear_db: bool = True):
    path = Path(jsonl_path)
    if not path.exists():
        log.error(f"❌ File not found: {path}")
        return

    if clear_db:
        log.info("🧹 Clearing existing vector database and manifest...")
        if FAISS_INDEX_DIR.exists():
            shutil.rmtree(FAISS_INDEX_DIR)
        FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
        ingest.reset_manifest()

    docs = []
    log.info(f"📖 Reading crawler data from {path.name}...")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Prioritize the 'search_text_keyword' field from the crawler as it includes headings context
            content = data.get("search_text_keyword") or data.get("text")
            if not content:
                continue
            
            # Use 'url' as the source for citations in the RAG chain
            source_url = data.get("url", "https://customer.payglobal.com/")
            
            # Create a rich metadata mapping
            meta = {
                "source_file": source_url,
                "file_type": "html",
                "title": data.get("title", "PayGlobal Documentation"),
                "chunk_type": data.get("chunk_type", "general"),
                "module": "ESS (Employee Self-Service)"
            }
            docs.append(Document(page_content=content, metadata=meta))

    log.info(f"✅ Loaded {len(docs)} documents.")
    
    if not docs:
        log.warning("⚠️ No valid chunks found to import.")
        return

    log.info("🧠 Initializing HuggingFace embedding model...")
    embeddings = ingest._get_embeddings()
    
    log.info("🚀 Batch inserting documents into FAISS index...")
    ingest._upsert_chunks(docs, embeddings, batch_size=200)
    
    log.info("🎉 Ingestion complete! The chatbot is ready to use the new data.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import PayGlobal crawler RAG records into Chatbot FAISS index")
    parser.add_argument("jsonl_file", help="Path to the .jsonl output file from the crawler")
    parser.add_argument("--append", action="store_true", help="Append instead of clearing the existing database")
    args = parser.parse_args()
    
    # We clear the DB by default unless --append is specified
    import_jsonl(args.jsonl_file, clear_db=not args.append)
