import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
DATA_DIR        = BASE_DIR / "data"
RAW_DOCS_DIR    = DATA_DIR / "raw"
UPLOADS_DIR     = DATA_DIR / "uploads"
FAISS_INDEX_DIR = DATA_DIR / "faiss_index"
DB_PATH         = str(DATA_DIR / "payglobal.db")
SYSTEM_PROMPT_PATH = BASE_DIR / "prompts" / "system_prompt.txt"

# Auto-create required directories
for d in [RAW_DOCS_DIR, UPLOADS_DIR, FAISS_INDEX_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Grok (xAI) LLM ────────────────────────────────────────────────────────
GROK_API_KEY  = os.getenv("GROK_API_KEY", "")
GROK_BASE_URL = "https://api.x.ai/v1"
GROK_MODEL    = os.getenv("GROK_MODEL", "grok-3")

# ── Embeddings (local HuggingFace — no API key required) ──────────────────
# Model is downloaded once (~90 MB) and cached in ~/.cache/huggingface/
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ── RAG Tuning ─────────────────────────────────────────────────────────────
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 150
RETRIEVER_K   = 5
MEMORY_WINDOW = 6   # conversation turns to keep in memory

# ── App ────────────────────────────────────────────────────────────────────
APP_TITLE = "PayGlobal AI Assistant"
APP_ICON  = "🌐"

PAYGLOBAL_MODULES = [
    "All Modules",
    "Payroll",
    "ESS (Employee Self-Service)",
    "HR Management",
    "Leave Management",
    "Recruitment",
    "Time & Attendance",
    "Benefits",
    "General / Other",
]

# ── Default Admin Credentials (change after first login) ──────────────────
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "PayGlobal@2024"
