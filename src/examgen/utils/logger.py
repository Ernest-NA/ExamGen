from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from platformdirs import user_log_dir


def set_logging() -> None:
    log_dir = Path(user_log_dir("ExamGen"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"examgen_{datetime.now():%Y%m%d_%H%M}.log"
    handlers = [
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3),
    ]
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )
