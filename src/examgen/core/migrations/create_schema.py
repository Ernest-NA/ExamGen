from __future__ import annotations

from examgen.core.database import get_engine
from examgen.core.models import Base

# No prerequisites: this migration creates the initial schema
requires: set[str] = set()
# Tables provided after running this migration
provides: set[str] = set(Base.metadata.tables)


def run() -> None:
    """Create all tables if they don't exist."""
    eng = get_engine()
    Base.metadata.create_all(eng)
