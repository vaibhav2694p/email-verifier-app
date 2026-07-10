from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict


class JobService:
    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def create_job(self, payload: Dict[str, Any] | None = None) -> str:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "payload": payload or {},
                "result": None,
                "error": "",
            }
        return job_id

    def update_job(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            self._jobs[job_id].update(updates)
            self._jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

    def get_job(self, job_id: str) -> Dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None


job_service = JobService()
