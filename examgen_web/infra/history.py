from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

# Reutilizamos directorio local del usuario (igual filosofía que config.py)
try:
    from platformdirs import user_data_dir  # type: ignore
except Exception:
    user_data_dir = None  # type: ignore

APP_NAME = "ExamGen"

def _base_dir() -> Path:
    if user_data_dir:
        base = Path(user_data_dir(APP_NAME))
    else:
        base = Path.home() / f".{APP_NAME.lower()}"
    base.mkdir(parents=True, exist_ok=True)
    return base

def _events_path() -> Path:
    d = _base_dir() / "history"
    d.mkdir(parents=True, exist_ok=True)
    return d / "events.jsonl"

@dataclass
class Event:
    ts: str
    exam_id: Optional[int]
    entity: str
    action: str
    entity_id: Optional[int]
    summary: Optional[str]
    before: Optional[dict]
    after: Optional[dict]
    extra: Optional[dict]
    source: str = "web"

def record_event(
    *,
    exam_id: Optional[int],
    entity: str,
    action: str,
    entity_id: Optional[int] = None,
    summary: Optional[str] = None,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    extra: Optional[dict] = None,
) -> None:
    event = Event(
        ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        exam_id=exam_id,
        entity=entity,
        action=action,
        entity_id=entity_id,
        summary=summary,
        before=before,
        after=after,
        extra=extra,
    )
    p = _events_path()
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event.__dict__, ensure_ascii=False) + "\n")

def list_events_for_exam(exam_id: int, limit: int = 25) -> list[dict]:
    p = _events_path()
    if not p.exists():
        return []
    # Estrategia simple: leer todo y filtrar (válido en local para tamaños típicos)
    with p.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    out: list[dict] = []
    for line in reversed(lines):
        try:
            ev = json.loads(line)
            if ev.get("exam_id") == exam_id:
                out.append(ev)
                if len(out) >= limit:
                    break
        except Exception:
            continue
    return out
