from __future__ import annotations
from contextlib import contextmanager
from typing import Generator, Any, Optional

from sqlalchemy import create_engine, text  # type: ignore
from sqlalchemy.orm import sessionmaker  # type: ignore

from .config import load_settings

# Intento de reutilizar la sesión del dominio
try:
    # Debe existir algo como: examgen/data/session.py con get_session()
    from examgen.data.session import get_session as domain_get_session  # type: ignore[attr-defined]
except Exception:
    domain_get_session = None  # type: ignore

_settings = load_settings()

# Fallback interno (no crea tablas)
_engine = None
_SessionLocal: Optional[sessionmaker] = None


def _ensure_fallback_sessionmaker():
    global _engine, _SessionLocal
    if _SessionLocal is None:
        connect_args = {}
        if _settings.db_url.startswith("sqlite:///"):
            # Permitir acceso desde hilos del servidor dev
            connect_args = {"check_same_thread": False}
        _engine = create_engine(
            _settings.db_url, future=True, connect_args=connect_args
        )
        _SessionLocal = sessionmaker(
            bind=_engine, autoflush=False, autocommit=False, future=True
        )


@contextmanager
def get_session() -> Generator[Any, None, None]:
    """
    Devuelve una sesión de BD.
    - Si el dominio expone get_session(), la usamos.
    - Si no, usamos un sessionmaker local (fallback), sin crear tablas.
    """
    if domain_get_session:
        with domain_get_session() as s:  # type: ignore[misc]
            yield s
        return

    _ensure_fallback_sessionmaker()
    assert _SessionLocal is not None
    s = _SessionLocal()
    try:
        yield s
    finally:
        s.close()


def ping() -> dict:
    """
    Verifica conectividad de BD ejecutando 'SELECT 1'.
    """
    try:
        with get_session() as s:
            s.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
