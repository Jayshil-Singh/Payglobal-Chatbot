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

# ── LLM — Groq (free tier) ───────────────────────────────────────────────────
# Get a free API key at: https://console.groq.com  (no credit card needed)
# Compatible models (all free): llama-3.3-70b-versatile, llama3-8b-8192,
#                                mixtral-8x7b-32768, gemma2-9b-it
GROK_API_KEY  = os.getenv("GROK_API_KEY", "")
GROK_BASE_URL = os.getenv("GROK_BASE_URL", "https://api.groq.com/openai/v1")
GROK_MODEL    = os.getenv("GROK_MODEL",    "llama-3.3-70b-versatile")

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

# ── Admin Bootstrap (one-time) ─────────────────────────────────────────────
# Leave ADMIN_BOOTSTRAP_PASSWORD empty after first setup to disable auto-bootstrap.
DEFAULT_ADMIN_USER = os.getenv("ADMIN_BOOTSTRAP_USER", "admin")
DEFAULT_ADMIN_PASS = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "")

# ── Security ────────────────────────────────────────────────────────────────
# Keep disabled in production. Enabling allows pickle-backed FAISS loads.
ALLOW_DANGEROUS_DESERIALIZATION = os.getenv("ALLOW_DANGEROUS_DESERIALIZATION", "false").lower() == "true"
# Cloud-safe default: keep heavy cross-encoder reranker off unless explicitly enabled.
ENABLE_RERANKER = os.getenv("ENABLE_RERANKER", "false").lower() == "true"

# ── Rate Limiting ──────────────────────────────────────────────────────────
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "50"))

# ── Authentication / Account Security ──────────────────────────────────────
PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
MAX_FAILED_LOGIN_ATTEMPTS = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))
SESSION_IDLE_TIMEOUT_MINUTES = int(os.getenv("SESSION_IDLE_TIMEOUT_MINUTES", "60"))

# ── SMTP (new user onboarding emails) ──────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# ── SendGrid API fallback (recommended if SMTP ports are blocked) ──────────
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "")

