from __future__ import annotations

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from platformdirs import user_log_dir


class _Null(logging.Handler):
    """Handler that discards all records."""

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        """Do nothing."""
        pass


def set_logging() -> None:
    """Configure root logger according to ``settings.debug_mode``."""
    from examgen.config import settings

    root = logging.getLogger()
    root.handlers.clear()

    if settings.debug_mode:
        log_dir = Path(user_log_dir("ExamGen"))
        log_dir.mkdir(parents=True, exist_ok=True)
        file_h = RotatingFileHandler(
            log_dir / f"examgen_{datetime.now():%Y%m%d_%H%M}.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_h.setLevel(logging.DEBUG)
        root.addHandler(file_h)
        root.setLevel(logging.DEBUG)
    else:
        root.addHandler(_Null())
        root.setLevel(logging.CRITICAL)
