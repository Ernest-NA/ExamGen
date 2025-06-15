from __future__ import annotations

from datetime import datetime
import json
import sys
import time

from examgen.config import settings

_prev_render_ts: float | None = None


def jlog(evt: str, **extra: object) -> None:
    """Emit a JSON line with *evt* and any *extra* fields."""
    if not settings.debug_mode:
        return
    now = datetime.now().isoformat(timespec="milliseconds")
    rec = {"ts": now, "evt": evt, **extra}
    print(json.dumps(rec, ensure_ascii=False), file=sys.stderr)


def log(msg: str) -> None:
    """Compatibility wrapper for plain text logs."""
    jlog("log", message=msg)


def mark_render_start() -> None:
    """Store the current time to compute render latency."""
    global _prev_render_ts
    _prev_render_ts = time.perf_counter()


def render_elapsed() -> int:
    """Return elapsed milliseconds since ``mark_render_start``."""
    start = _prev_render_ts or time.perf_counter()
    return int((time.perf_counter() - start) * 1000)
