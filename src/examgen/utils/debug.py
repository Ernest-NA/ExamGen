from examgen.config import settings


def log(msg: str) -> None:
    """Print *msg* when debug mode is active."""
    if getattr(settings, "debug_mode", False):
        print(f"[DEBUG] {msg}")
