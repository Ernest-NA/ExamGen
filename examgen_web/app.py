import os
import sys
from pathlib import Path
from . import create_app

# Asegura que 'src/' esté en sys.path para importar 'examgen' en modo editable
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.exists():
    src_path = str(SRC)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

# Instancia global para test clients y flask CLI
app = create_app()


def _get_bool(env_value: str | None, default: bool = False) -> bool:
    if env_value is None:
        return default
    return env_value.lower() in ("1", "true", "yes", "on")


if __name__ == "__main__":
    host = os.getenv("EXAMGEN_HOST", "127.0.0.1")
    port = int(os.getenv("EXAMGEN_PORT", "5000"))
    debug = _get_bool(os.getenv("EXAMGEN_DEBUG"), True)
    app.run(host=host, port=port, debug=debug)
