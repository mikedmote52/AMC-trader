# keep package importable and re-export shared symbols if present
try:
    from .discover import select_candidates, main  # type: ignore
except Exception:
    pass