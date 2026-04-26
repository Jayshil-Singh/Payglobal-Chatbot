"""
Text chunking: splits large documents into smaller, overlapping chunks
with metadata preserved for source citation.
"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.logger import get_logger

log = get_logger(__name__)

_HEADING_MIN_LEN = 4
_HEADING_MAX_LEN = 90


def _looks_like_heading(line: str) -> bool:
    s = (line or "").strip()
    if len(s) < _HEADING_MIN_LEN or len(s) > _HEADING_MAX_LEN:
        return False
    # Heuristics: ALL CAPS, Title-like ending ":", or numbered sections.
    if s.endswith(":"):
        return True
    if s[:1].isdigit() and any(ch == "." for ch in s[:6]):
        return True
    letters = [ch for ch in s if ch.isalpha()]
    if letters and sum(ch.isupper() for ch in letters) / max(1, len(letters)) > 0.85:
        return True
    return False


def _split_docx_by_headings(doc: Document) -> list[Document]:
    text = doc.page_content or ""
    lines = [ln.rstrip() for ln in text.splitlines()]
    sections: list[tuple[str, list[str]]] = []
    current_title = doc.metadata.get("section") or ""
    current_lines: list[str] = []

    for ln in lines:
        if _looks_like_heading(ln):
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = ln.strip().strip(":")[:120]
            current_lines = []
        else:
            current_lines.append(ln)

    if current_lines:
        sections.append((current_title, current_lines))

    out: list[Document] = []
    for title, body_lines in sections:
        body = "\n".join([b for b in body_lines if b.strip()])
        if not body.strip():
            continue
        meta = dict(doc.metadata)
        if title:
            meta["section"] = title
        out.append(Document(page_content=body, metadata=meta))
    return out or [doc]


def chunk_documents(
    docs: list[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[Document]:
    """
    Split documents into overlapping chunks.
    Preserves source metadata from each parent document.
    """
    expanded: list[Document] = []
    for d in docs:
        if (d.metadata or {}).get("file_type") == "docx":
            expanded.extend(_split_docx_by_headings(d))
        else:
            expanded.append(d)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(expanded)
    log.info(f"Split {len(docs)} document(s) into {len(chunks)} chunk(s)")
    return chunks
