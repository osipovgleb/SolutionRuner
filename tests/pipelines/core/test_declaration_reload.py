"""Changes in split registration files are visible after a live reload."""

import importlib
import sys

import pytest

from solution_runner.pipelines.core.declaration_reload import reload_declarations


@pytest.mark.parametrize(
    ("root", "attribute"), [("profiles", "PROFILES"), ("handlers", "HANDLERS")]
)
def test_reload_refreshes_nested_declaration_dependencies(
    tmp_path, monkeypatch, root, attribute
):
    package_name = f"reload_test_{root}"
    package = tmp_path / package_name
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    leaf = package / f"leaf_{root}.py"
    middle = package / f"middle_{root}.py"
    leaf.write_text(f"{attribute} = ('before',)\n", encoding="utf-8")
    middle.write_text(f"from .leaf_{root} import {attribute}\n", encoding="utf-8")
    (package / f"{root}.py").write_text(
        f"from .middle_{root} import {attribute}\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    module_name = f"{package_name}.{root}"
    try:
        assert getattr(importlib.import_module(module_name), attribute) == ("before",)
        leaf.write_text(f"{attribute} = ('after-update',)\n", encoding="utf-8")
        assert getattr(reload_declarations(module_name), attribute) == ("after-update",)
    finally:
        for name in list(sys.modules):
            if name == package_name or name.startswith(package_name + "."):
                sys.modules.pop(name)
