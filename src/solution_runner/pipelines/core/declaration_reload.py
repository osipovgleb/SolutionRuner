"""Reload split profile and handler declarations before their aggregators."""

from __future__ import annotations

import ast
from importlib import import_module, reload
from importlib.util import resolve_name
from pathlib import Path
from types import ModuleType


def reload_declarations(module_name: str) -> ModuleType:
    """Reload local declaration dependencies first, then their parent module."""

    visited: set[str] = set()

    def visit(name: str) -> ModuleType:
        module = import_module(name)
        if name in visited:
            return module
        visited.add(name)
        path = Path(module.__file__ or "")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for statement in tree.body:
            if not isinstance(statement, ast.ImportFrom) or not statement.level:
                continue
            target = statement.module or ""
            if not target.rsplit(".", 1)[-1].endswith(("_profiles", "_handlers")):
                continue
            dependency = resolve_name(
                "." * statement.level + target, module.__package__
            )
            visit(dependency)
        return reload(module)

    return visit(module_name)
