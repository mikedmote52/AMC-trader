import importlib, sys, os
from pathlib import Path

# Ensure /app is on sys.path (Render working dir); backend folder is under it
root = Path(__file__).resolve().parents[2]   # …/backend/../
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# Prefer backend.src.* (always present in this repo)
_backend_src = importlib.import_module("backend.src")
sys.modules.setdefault("app", _backend_src)
sys.modules.setdefault("app.main", importlib.import_module("backend.src.app"))
try:
    sys.modules.setdefault("app.routes", importlib.import_module("backend.src.routes"))
except Exception:
    pass