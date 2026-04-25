"""
Text chunking: splits large documents into smaller, overlapping chunks
with metadata preserved for source citation.
"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.logger import get_logger

log = get_logger(__name__)


def chunk_documents(
    docs: list[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[Document]:
    """
    Split documents into overlapping chunks.
    Preserves source metadata from each parent document.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(docs)
    log.info(f"Split {len(docs)} document(s) into {len(chunks)} chunk(s)")
    return chunks
