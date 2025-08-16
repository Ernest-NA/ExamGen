from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def append_event(event: str, **data: Any) -> None:
    """Append an event to ``logs/web_events.jsonl``.

    Parameters
    ----------
    event:
        Nombre del evento.
    data:
        Datos adicionales serializables.
    """
    log_path = Path("logs/web_events.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"event": event, "ts": datetime.utcnow().isoformat(), **data}
    with log_path.open("a", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
        fh.write("\n")


def log_question_cloned(
    original_id: int,
    new_id: int,
    user: str | None = None,
    changes: dict | None = None,
) -> None:
    """Convenience wrapper for ``questions.cloned`` event."""
    append_event(
        "questions.cloned",
        original_id=original_id,
        new_id=new_id,
        user=user,
        changes=changes or {},
    )


def log_language_set(lang: str) -> None:
    """Registrar cambio de idioma en ``logs/web_events.jsonl``."""
    append_event("i18n.language_set", lang=lang)
