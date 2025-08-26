# backend/app/__init__.py
import importlib, sys
# Map package 'app' to 'src'
_src = importlib.import_module("src")
sys.modules.setdefault("app", _src)
# Also alias common submodules
sys.modules.setdefault("app.main", importlib.import_module("src.app"))
sys.modules.setdefault("app.routes", importlib.import_module("src.routes"))