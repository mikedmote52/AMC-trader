# backend/app/__init__.py
import importlib, sys, os
from pathlib import Path
_here = Path(__file__).resolve()
_backend_root = _here.parent.parent  # …/backend
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))
_src = importlib.import_module("src")
sys.modules.setdefault("app", _src)
sys.modules.setdefault("app.main", importlib.import_module("src.app"))
try:
    sys.modules.setdefault("app.routes", importlib.import_module("src.routes"))
except Exception:
    pass