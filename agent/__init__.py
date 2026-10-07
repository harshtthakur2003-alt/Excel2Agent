"""Excel-driven, reusable AI workflow agent."""
from __future__ import annotations

from pathlib import Path

try:  # load .env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # pragma: no cover
    pass

from .graph import WorkflowAgent  # noqa: E402
from .registry import WorkflowRegistry  # noqa: E402

__all__ = ["WorkflowAgent", "WorkflowRegistry"]
