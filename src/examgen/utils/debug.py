from __future__ import annotations

from datetime import datetime
import json
import logging
import os
import time
import uuid

from examgen.config import settings

_session_id = uuid.uuid4().hex[:8]
_render_t0 = 0.0


def mark_render_start() -> None:
    """Record starting timestamp for render latency."""
    global _render_t0
    _render_t0 = time.perf_counter()


def jlog(evt: str, **extra: object) -> None:
    """Write a JSON line if debug mode is active."""
    if not settings.debug_mode:
        return
    record = {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "evt": evt,
        "sess": _session_id,
        "pid": os.getpid(),
        **extra,
    }
    logging.getLogger("examgen").debug(json.dumps(record, ensure_ascii=False))


def render_elapsed_ms() -> int:
    """Return elapsed milliseconds since :func:`mark_render_start`."""
    return int((time.perf_counter() - _render_t0) * 1000)


def log(msg: str) -> None:
    """Compatibility wrapper for plain text logs."""
    jlog("log", message=msg)
