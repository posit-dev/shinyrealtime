"""Internal helpers extracted so they can be unit-tested without importing the
heavier realtime module (which pulls in aiohttp/openai/chatlas).
"""

import json
from typing import Any


def _coerce_output(x: Any, fallback: str = "OK") -> str:
    """Coerce tool result to non-empty scalar string per Realtime API spec.

    Strings pass through unchanged. int/float/bool are stringified. Anything
    else (dicts, lists, dataclasses via ``__dict__``) is JSON-serialized so
    the model receives structured data. Returns ``fallback`` for ``None``,
    empty containers, or empty strings.
    """
    if x is None:
        return fallback
    try:
        if isinstance(x, str):
            s = x
        elif isinstance(x, (int, float, bool)):
            s = str(x)
        else:
            s = json.dumps(x)
    except Exception:
        return fallback
    if not s:
        return fallback
    return s
