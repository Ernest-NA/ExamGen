"""examgen/auth.py – Gestión de usuarios y autenticación.

Separamos la lógica de usuarios/contraseñas del resto de modelos para
mantener el código modular.

• `User`       – ORM model.  Almacena usuario, hash bcrypt y tema preferido.
• `create_user` – helper para registrar un usuario nuevo.
• `login`       – helper para verificar credenciales y devolver objeto User.

Requiere `bcrypt` → pip install bcrypt
"""
from __future__ import annotations
import datetime as _dt

import os
import platform
from pathlib import Path
from typing import Optional
from typing import List

import bcrypt
from sqlalchemy import String, create_engine
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from examgen.models import Base  # usa la misma DeclarativeBase y metadata

# -----------------------------------------------------------------------------
# Configuración ruta BD (reusa la lógica de examgen.models)
# -----------------------------------------------------------------------------

def default_db_path() -> Path:
    """Devuelve la ruta donde se guarda la BD fuera del repo de código."""
    if platform.system() == "Windows":
        base = Path(os.environ["LOCALAPPDATA"]) / "ExamGen"
    else:
        base = Path.home() / ".local" / "share" / "examgen"
    base.mkdir(parents=True, exist_ok=True)
    return base / "examgen.db"


def get_engine(db_path: str | Path | None = None):
    if db_path is None:
        db_path = default_db_path()
    return create_engine(f"sqlite:///{db_path}", future=True)


# -----------------------------------------------------------------------------
# ORM: tabla USER
# -----------------------------------------------------------------------------
class User(Base):
    __tablename__ = "user"

    username: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    email:    Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 hex
    theme:    Mapped[str] = mapped_column(String(10), default="dark", nullable=False)

    created_at: Mapped[_dt.datetime] = mapped_column(default=_dt.datetime.utcnow)
    bio:        Mapped[str | None]   = mapped_column(Text())

    # relaciones opcionales con preguntas / exámenes se definen en los modelos
    attempts: Mapped[List["Attempt"]] = relationship(back_populates="user")

    # ---------------------- helpers ---------------------
    def set_password(self, raw: str) -> None:
        self._password = bcrypt.hashpw(raw.encode(), bcrypt.gensalt())

    def check_password(self, raw: str) -> bool:
        return bcrypt.checkpw(raw.encode(), self._password)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.username!r} {self.email!r}>"

# -----------------------------------------------------------------------------
# API de alto nivel
# -----------------------------------------------------------------------------

def create_user(username: str, password: str, *, theme: str = "dark", db_path: str | Path | None = None) -> User:
    """Crea y persiste un nuevo usuario.  Lanza ValueError si ya existe."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    with Session(engine) as s:
        if s.query(User).filter_by(username=username.lower().strip()).first():
            raise ValueError("El usuario ya existe")
        u = User(username=username.lower().strip(), theme=theme)
        u.set_password(password)
        s.add(u); s.commit(); s.refresh(u)
        return u


def login(username: str, password: str, *, db_path: str | Path | None = None) -> Optional[User]:
    """Devuelve User si la contraseña es correcta, None en caso contrario."""
    engine = get_engine(db_path)
    with Session(engine) as s:
        u: User | None = s.query(User).filter_by(username=username.lower().strip()).first()
        if u and u.check_password(password):
            return u
        return None


# -----------------------------------------------------------------------------
# Uso rápido desde CLI
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import getpass, sys

    eng = get_engine()
    Base.metadata.create_all(eng)

    print("ExamGen – Gestión de usuarios\n")
    action = input("[1] Crear usuario  [2] Login  > ").strip()

    if action == "1":
        usr = input("Nuevo usuario: ").strip()
        pwd = getpass.getpass("Contraseña: ")
        email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
        try:
            create_user(usr, pwd)
            print("✔️  Usuario creado.")
        except ValueError as e:
            print(e)
            sys.exit(1)
    elif action == "2":
        usr = input("Usuario: ")
        pwd = getpass.getpass("Contraseña: ")
        if login(usr, pwd):
            print("✅ Login OK")
        else:
            print("❌ Usuario o contraseña incorrectos")
    else:
        print("Opción no válida")
