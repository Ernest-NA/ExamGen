from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Iterable

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
TMP_DIR = Path(tempfile.gettempdir()) / "examgen"
TMP_DIR.mkdir(parents=True, exist_ok=True)


class UploadError(Exception):
    """Raised when an uploaded file fails validation."""


def save_upload(
    file: FileStorage,
    *,
    allowed_extensions: Iterable[str],
    max_size: int = MAX_UPLOAD_SIZE,
) -> Path:
    """Save an uploaded file to a temporary location.

    Args:
        file: Werkzeug ``FileStorage`` uploaded by the user.
        allowed_extensions: Iterable of allowed extensions (e.g. {'.json', '.csv'}).
        max_size: Maximum allowed size in bytes.

    Returns:
        Path to the saved file.
    """
    filename = secure_filename(file.filename or "")
    ext = Path(filename).suffix.lower()
    if ext not in {e.lower() for e in allowed_extensions}:
        raise UploadError("Extensión no permitida")

    # Check size
    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > max_size:
        raise UploadError("Archivo demasiado grande")

    token = uuid.uuid4().hex
    dest = TMP_DIR / f"{token}{ext}"
    file.save(dest)
    return dest


def cleanup(path: Path) -> None:
    """Remove a temporary file, ignoring errors."""
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass
