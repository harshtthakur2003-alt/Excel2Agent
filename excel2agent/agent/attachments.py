"""Turn user attachments into workflow inputs.

* ``.json``  -> merged as structured data (e.g. {"product": {...}})
* ``.csv`` / ``.xlsx`` -> passed as a file-path parameter (keyword lists -> ``keywords_path``,
  anything else -> ``file_path``). The router only applies keys the selected workflow declares.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_attachments(paths: list[str]) -> dict:
    out: dict = {}
    for p in paths or []:
        path = Path(p)
        if not path.exists():
            raise FileNotFoundError(f"Attachment not found: {p}")
        suffix = path.suffix.lower()
        if suffix == ".json":
            out.update(json.loads(path.read_text(encoding="utf-8")))
        elif suffix in (".csv", ".xlsx"):
            key = "keywords_path" if "keyword" in path.name.lower() else "file_path"
            out[key] = str(path)
        else:
            raise ValueError(f"Unsupported attachment type: {p} (use .json, .csv or .xlsx)")
    return out
