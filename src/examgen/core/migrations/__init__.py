from __future__ import annotations

from . import create_schema, add_section

# Each migration module exposes:
#   requires: set[str]  -- tables needed
#   provides: set[str]  -- tables created
#   def run() -> None   -- perform migration

MIGRATIONS = (
    create_schema,  # provides base tables
    add_section,    # requires question
)
