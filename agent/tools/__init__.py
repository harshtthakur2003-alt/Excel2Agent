"""Tool registry.

Every capability a workflow step can use is a plain Python function registered
with ``@register_tool``. Workflows reference tools *by name* from
``config/workflow_bindings.yaml`` - so a new workflow that only re-uses existing
tools needs zero Python changes, and a new capability is one decorated function.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class ToolContext:
    """Everything a tool may need, injected by the executor."""
    params: dict                      # parameters extracted from the user request
    settings: dict                    # workflow-level settings from the YAML binding
    data: dict                        # outputs of previous steps (the "blackboard")
    base_dir: Path                    # project root, for resolving relative paths
    llm: Any = None                   # agent.llm.LLMClient (may be offline)
    workflow: Any = None              # WorkflowSpec
    run_id: str = ""
    extras: dict = field(default_factory=dict)

    def path(self, p: str) -> Path:
        path = Path(p)
        return path if path.is_absolute() else self.base_dir / path


@dataclass
class ToolInfo:
    name: str
    func: Callable
    category: str
    description: str


_REGISTRY: dict[str, ToolInfo] = {}


def register_tool(name: str, category: str = "general", description: str = ""):
    def decorator(func: Callable) -> Callable:
        if name in _REGISTRY and _REGISTRY[name].func is not func:
            raise ValueError(f"Tool '{name}' registered twice")
        _REGISTRY[name] = ToolInfo(name, func, category, description or (func.__doc__ or "").strip())
        return func
    return decorator


def get_tool(name: str) -> Optional[ToolInfo]:
    load_all_tools()
    return _REGISTRY.get(name)


def all_tools() -> dict[str, ToolInfo]:
    load_all_tools()
    return dict(_REGISTRY)


_LOADED = False


def load_all_tools() -> None:
    """Import every module in this package so their decorators run (plugin discovery)."""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    for mod in pkgutil.iter_modules(__path__):
        importlib.import_module(f"{__name__}.{mod.name}")
