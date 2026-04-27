from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, "-m", "alembic", "-c", str(root / "alembic.ini"), "upgrade", "head"]
    proc = subprocess.run(cmd, cwd=str(root), check=False)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

