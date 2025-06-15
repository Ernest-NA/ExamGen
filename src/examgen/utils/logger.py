from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from platformdirs import user_log_dir


def set_logging() -> None:
    """Configure root logger according to ``settings.debug_mode``."""
    from examgen.config import settings

    root = logging.getLogger()
    while root.handlers:
        root.removeHandler(root.handlers[0])

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    debug_h = logging.StreamHandler(sys.stderr)
    debug_h.setLevel(logging.DEBUG)
    debug_h.setFormatter(fmt)
    root.addHandler(debug_h)

    if settings.debug_mode:
        log_dir = Path(user_log_dir("ExamGen"))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"examgen_{datetime.now():%Y%m%d_%H%M}.log"
        file_h = RotatingFileHandler(
            log_file, maxBytes=1_000_000, backupCount=3
        )
        file_h.setLevel(logging.DEBUG)
        file_h.setFormatter(fmt)
        root.addHandler(file_h)

    root.setLevel(logging.DEBUG if settings.debug_mode else logging.INFO)
    logging.info("Logging inicializado (debug=%s)", settings.debug_mode)
