from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from examgen.utils.debug import log
from examgen.config import DEFAULT_DB

from examgen.core.models import Base, _create_examiner_tables


_engine: Engine | None = None
SessionLocal = sessionmaker(expire_on_commit=False, future=True)

LEGACY_DB = Path("examgen.db")


def set_engine(db_path: Path | None = None) -> None:
    """Create and register a new engine bound to ``db_path``."""
    global _engine

    path = db_path or DEFAULT_DB

    if not path.exists():
        if LEGACY_DB.exists():
            LEGACY_DB.rename(path)
        else:
            path.touch()
            log(f"DB creada en {path}")

    _engine = create_engine(f"sqlite:///{path}", echo=False, future=True)
    SessionLocal.configure(bind=_engine)
    init_db(_engine)


def get_engine() -> Engine:
    """Return the currently configured engine."""
    if _engine is None:
        raise RuntimeError("Engine not initialised. Call set_engine() first")
    return _engine


def init_db(engine: Engine) -> None:
    """Create tables and apply idempotent migrations."""
    Base.metadata.create_all(engine)

    _create_examiner_tables(engine)

    with engine.begin() as con:
        con.exec_driver_sql("PRAGMA foreign_keys = ON")

        existing_cols = {
            tbl: {row[1] for row in con.exec_driver_sql(f"PRAGMA table_info({tbl})")}
            for tbl in ("question", "answer_option")
        }

        if (
            "reference" not in existing_cols["question"]
            and "reference_id" not in existing_cols["question"]
        ):
            con.exec_driver_sql("ALTER TABLE question ADD COLUMN reference TEXT")

        for col_sql in ("answer TEXT", "explanation TEXT"):
            col_name = col_sql.split()[0]
            if col_name not in existing_cols["answer_option"]:
                con.exec_driver_sql(f"ALTER TABLE answer_option ADD COLUMN {col_sql}")


def run_migrations() -> None:
    """Execute optional migration scripts if dependencies are met."""
    from .migrations import MIGRATIONS

    engine = get_engine()
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for mig in MIGRATIONS:
        if mig.requires.issubset(existing_tables):
            try:
                mig.run()
                existing_tables.update(mig.provides)
            except OperationalError as exc:
                log(f"Migration {mig.__name__} failed: {exc}")
        else:
            missing = mig.requires - existing_tables
            log(f"Skipping {mig.__name__}: unmet deps {missing}")
