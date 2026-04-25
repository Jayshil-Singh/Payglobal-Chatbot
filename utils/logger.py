import logging
import re
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


_REDACT_PATTERNS = [
    # Authorization headers / bearer tokens
    (re.compile(r"(?i)(authorization\\s*[:=]\\s*bearer\\s+)[^\\s]+"), r"\\1[REDACTED]"),
    (re.compile(r"(?i)(bearer\\s+)[^\\s]+"), r"\\1[REDACTED]"),
    # Common env-style secrets in logs
    (re.compile(r"(?i)(GROK_API_KEY\\s*[:=]\\s*)[^\\s]+"), r"\\1[REDACTED]"),
    (re.compile(r"(?i)(SENDGRID_API_KEY\\s*[:=]\\s*)[^\\s]+"), r"\\1[REDACTED]"),
    (re.compile(r"(?i)(SMTP_PASSWORD\\s*[:=]\\s*)[^\\s]+"), r"\\1[REDACTED]"),
]


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            for pat, repl in _REDACT_PATTERNS:
                msg = pat.sub(repl, msg)
            record.msg = msg
            record.args = ()
        except Exception:
            pass
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler — force UTF-8 on Windows
    import io
    ch = logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'))
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    ch.addFilter(RedactingFilter())
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(LOG_DIR / "payglobal_bot.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    fh.addFilter(RedactingFilter())
    logger.addHandler(fh)

    return logger
