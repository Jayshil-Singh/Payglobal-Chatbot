"""
Document loaders: PDF, DOCX, and web URLs.
Returns a flat list of LangChain Document objects.
"""
from pathlib import Path

from langchain_core.documents import Document

from utils.logger import get_logger

log = get_logger(__name__)


def load_pdfs(folder: Path) -> list[Document]:
    """Load all PDFs from a directory using pypdf."""
    from langchain_community.document_loaders import PyMuPDFLoader
    docs = []
    pdf_files = list(folder.glob("**/*.pdf"))
    log.info(f"Found {len(pdf_files)} PDF(s) in {folder}")
    for pdf in pdf_files:
        try:
            loader = PyMuPDFLoader(str(pdf))
            pages = loader.load()
            # Tag metadata
            for page in pages:
                page.metadata["source_file"] = pdf.name
                page.metadata["file_type"] = "pdf"
            docs.extend(pages)
            log.debug(f"  Loaded {len(pages)} pages from {pdf.name}")
        except Exception as e:
            log.warning(f"  Failed to load {pdf.name}: {e}")
    return docs


def load_docx(folder: Path) -> list[Document]:
    """Load all DOCX files from a directory."""
    from langchain_community.document_loaders import Docx2txtLoader
    docs = []
    docx_files = list(folder.glob("**/*.docx"))
    log.info(f"Found {len(docx_files)} DOCX file(s) in {folder}")
    for docx in docx_files:
        try:
            loader = Docx2txtLoader(str(docx))
            pages = loader.load()
            for page in pages:
                page.metadata["source_file"] = docx.name
                page.metadata["file_type"] = "docx"
            docs.extend(pages)
            log.debug(f"  Loaded {docx.name}")
        except Exception as e:
            log.warning(f"  Failed to load {docx.name}: {e}")
    return docs


def load_urls(urls: list[str]) -> list[Document]:
    """Load content from a list of web URLs."""
    from langchain_community.document_loaders import WebBaseLoader
    docs = []
    for url in urls:
        try:
            loader = WebBaseLoader(url)
            pages = loader.load()
            for page in pages:
                page.metadata["source_file"] = url
                page.metadata["file_type"] = "web"
            docs.extend(pages)
            log.debug(f"  Loaded URL: {url}")
        except Exception as e:
            log.warning(f"  Failed to load URL {url}: {e}")
    return docs


def load_all(folder: Path, urls: list[str] = None) -> list[Document]:
    """Load PDFs, DOCX, and optional URLs from a folder."""
    docs = []
    docs.extend(load_pdfs(folder))
    docs.extend(load_docx(folder))
    if urls:
        docs.extend(load_urls(urls))
    log.info(f"Total documents loaded: {len(docs)}")
    return docs
