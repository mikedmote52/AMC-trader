from __future__ import annotations
import json, gzip, zlib
from typing import Any, Mapping

_GZIP = b"\x1f\x8b"
_ZLIB_HEADERS = {b"\x78\x01", b"\x78\x9c", b"\x78\xda"}

def _maybe_decompress(raw: bytes, headers: Mapping[str, str]) -> bytes:
    """
    Safely decompress HTTP response bytes if they are gzip/deflate compressed.
    Handles both explicit Content-Encoding headers and magic byte detection.
    """
    enc = headers.get("Content-Encoding", "").lower()
    if "gzip" in enc:
        return gzip.decompress(raw)
    if "deflate" in enc:
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    if raw.startswith(_GZIP):
        return gzip.decompress(raw)
    if any(raw.startswith(h) for h in _ZLIB_HEADERS):
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw

def json_from_response_bytes(content: bytes, headers: Mapping[str, str]):
    """
    Safely parse JSON from HTTP response bytes, handling compression automatically.
    This prevents UnicodeDecodeError when Polygon API returns compressed responses.
    """
    data = _maybe_decompress(content, headers)
    return json.loads(data.decode("utf-8"))