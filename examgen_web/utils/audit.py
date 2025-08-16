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
