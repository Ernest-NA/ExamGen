#!/usr/bin/env python3
# ruff: noqa: E402
import sys
import shutil
import datetime
from pathlib import Path

# Permite ejecutar sin instalar el paquete
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))
if ROOT.exists():
    sys.path.insert(0, str(ROOT))

from examgen_web.infra.config import get_db_url  # type: ignore


def main(dst_dir: str | None = None) -> int:
    url = get_db_url()
    if not url.startswith("sqlite:///"):
        print("[!] Solo se soporta backup para SQLite en este script.")
        return 1

    db_path = Path(url.replace("sqlite:///", "", 1))
    if not db_path.exists():
        print(f"[!] Fichero de BD no encontrado: {db_path}")
        return 2

    dst = Path(dst_dir or (ROOT / "backups"))
    dst.mkdir(parents=True, exist_ok=True)

    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    out = dst / f"examgen-{ts}.db"
    shutil.copy2(db_path, out)
    print(f"[ok] Backup creado: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
