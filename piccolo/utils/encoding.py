from __future__ import annotations

import typing as t

try:
    import orjson

    ORJSON = True
except ImportError:
    import json

    ORJSON = False


def dump_json(data: t.Any) -> str:
    if ORJSON:
        return orjson.dumps(data, default=str).decode("utf8")
    else:
        return json.dumps(data, default=str)
