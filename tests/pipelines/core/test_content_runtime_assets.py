"""Shared-asset setup is deterministic in preview and in apply mode."""

from copy import deepcopy

from solution_runner.pipelines.core.content_runtime import (
    _ensure_required_assets,
    _with_required_assets,
)
from solution_runner.pipelines.equations.group_trigonometric import _ASSETS


RULE = "trigonometric-table-value-affine-argument"


def _context() -> dict:
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [{
                "key": "condition",
                "html": (
                    '<p>Найдите наименьший положительный корень '
                    '<span data-inline-latex="\\sin\\frac{\\pi x}{3}=\\frac{1}{2}"></span></p>'
                ),
            }],
        },
    }


class _Gateway:
    def __init__(self, context: dict) -> None:
        self.context = deepcopy(context)
        self.calls: list[str] = []

    def get_problem_context(self, problem_id: str) -> dict:
        assert problem_id == "problem"
        self.calls.append("read")
        return deepcopy(self.context)

    def apply_problem_transformations(self, problem_id: str, transformations: list[dict]) -> dict:
        assert problem_id == "problem"
        self.calls.append("create_solution")
        self.context["normalized_content"]["sections"].append({
            "key": "solution", "html": "<p></p>", "asset_keys": [],
        })
        return {"results": [{"problem_id": problem_id}]}

    def attach_source_asset_to_problems(self, **request) -> dict:
        self.calls.append("attach")
        asset_id = request["source_asset_id"]
        self.context["normalized_content"]["assets"].append({
            "asset_key": "shared_" + asset_id.replace("-", "")[:16],
            "asset_id": asset_id,
        })
        return {"outcomes": [{"problem_id": "problem", "ok": True}]}


def test_preview_models_missing_solution_and_matching_asset_without_mutating_context() -> None:
    original = _context()
    planned = _with_required_assets(original, RULE)

    assert len(original["normalized_content"]["sections"]) == 1
    assert original["normalized_content"]["assets"] == []
    assert any(item["key"] == "solution" for item in planned["normalized_content"]["sections"])
    assert planned["normalized_content"]["assets"] == [{
        "asset_key": "shared_33f5a2d29d364033",
        "asset_id": _ASSETS["sin-half.svg"],
    }]


def test_apply_creates_solution_then_attaches_selected_asset_and_rereads() -> None:
    gateway = _Gateway(_context())

    result = _ensure_required_assets(gateway, "problem", gateway.get_problem_context("problem"), RULE)

    assert gateway.calls == ["read", "create_solution", "read", "attach", "read"]
    assert any(item["key"] == "solution" for item in result["normalized_content"]["sections"])
    assert result["normalized_content"]["assets"][0]["asset_id"] == _ASSETS["sin-half.svg"]
