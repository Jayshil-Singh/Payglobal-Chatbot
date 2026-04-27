from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pg-job")
_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, Any]] = {}


def submit_job(name: str, fn: Callable[..., Any], *args, **kwargs) -> str:
    job_id = str(uuid.uuid4())
    with _LOCK:
        _JOBS[job_id] = {
            "id": job_id,
            "name": name,
            "status": "queued",
            "created_at": time.time(),
            "updated_at": time.time(),
            "result": None,
            "error": None,
        }

    def _run():
        _update(job_id, status="running")
        try:
            result = fn(*args, **kwargs)
            _update(job_id, status="done", result=result)
            return result
        except Exception as exc:  # pragma: no cover
            _update(job_id, status="failed", error=str(exc))
            raise

    future: Future = _EXECUTOR.submit(_run)
    _update(job_id, future=future)
    return job_id


def _update(job_id: str, **fields) -> None:
    with _LOCK:
        if job_id not in _JOBS:
            return
        _JOBS[job_id].update(fields)
        _JOBS[job_id]["updated_at"] = time.time()


def get_job(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        item = _JOBS.get(job_id)
        return dict(item) if item else None


def list_jobs(limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        items = sorted(_JOBS.values(), key=lambda x: x.get("updated_at", 0), reverse=True)
        return [dict(i) for i in items[:limit]]

