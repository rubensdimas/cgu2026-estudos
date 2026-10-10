import os
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://cgu:cgu@localhost:5432/cgu")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]
STATIC_DIR = Path(os.environ.get("STATIC_DIR", API_DIR.parent / "web" / "dist"))
DATA_DIR = Path(os.environ.get("DATA_DIR", API_DIR.parent.parent / "docs" / "data"))


def host_allowed(host: str | None) -> bool:
    if not host:
        return False
    for allowed in ALLOWED_HOSTS:
        if allowed == "*" or host == allowed or (allowed.startswith("*.") and host.endswith(allowed[1:])):
            return True
    return False
