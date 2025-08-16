from __future__ import annotations

import json
import shutil
import sqlite3
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

LOG_PATH = Path("logs/web_events.jsonl")
BACKUP_DIR = Path("backups")


def get_db_info(db_path: str) -> Dict[str, Any]:
    """Return database path, size and table stats."""
    info: Dict[str, Any] = {"path": db_path, "size": 0, "tables": []}
    db_file = Path(db_path)
    if db_file.exists():
        info["size"] = db_file.stat().st_size
        conn = sqlite3.connect(db_path)
        try:
            for row in conn.execute("PRAGMA table_list"):
                name = row[1]
                count = conn.execute(
                    f"SELECT COUNT(*) FROM {name}"
                ).fetchone()[0]
                info["tables"].append({"name": name, "rows": count})
        finally:
            conn.close()
    return info


def list_events(limit: int) -> List[Dict[str, Any]]:
    """Return last ``limit`` events from the audit log."""
    if not LOG_PATH.exists():
        return []
    lines: deque[str] = deque(maxlen=limit)
    with LOG_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            lines.append(line)
    events: List[Dict[str, Any]] = []
    for line in lines:
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        details = {k: v for k, v in raw.items() if k not in {"ts", "event"}}
        events.append(
            {
                "ts": raw.get("ts"),
                "event": raw.get("event"),
                "details": details,
            }
        )
    return events


def append_event(event: str, details: Dict[str, Any]) -> None:
    """Append an event with UTC timestamp to the audit log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": datetime.utcnow().isoformat(),
        "event": event,
        **details,
    }
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
        fh.write("\n")


def create_backup(src_path: str) -> str:
    """Copy ``src_path`` to ``backups/`` with a timestamped name."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"examgen_{ts}.db"
    shutil.copyfile(src_path, dest)
    return str(dest)


def save_uploaded_db(uploaded_file) -> str:
    """Save uploaded file to ``backups/`` with a unique name."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"upload_{ts}.db"
    dest = BACKUP_DIR / filename
    uploaded_file.save(dest)
    return str(dest)


def clear_history() -> None:
    """Remove the audit log file if present."""
    try:
        LOG_PATH.unlink()
    except FileNotFoundError:
        pass
