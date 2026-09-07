"""Regression tests for the group-26667 quadratic-root runner."""

from __future__ import annotations

from copy import deepcopy

import pytest

from solution_runner.pipelines.equations.group_26667_planner import (
    build_repair_plan,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.triangles.right.planner import (
    RightTrianglePlanError,
)


def _context(formula: str, *, kind: str = "меньший", answer: str = "") -> dict:
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [
                {
                    "key": "condition",
                    "section_id": "condition:1",
                    "transformation_target_id": "section:condition:1",
                    "asset_keys": [],
                    "html": (
                        '<p>Най­ди­те ко­рень урав­не­ния: '
                        f'<span data-inline-latex="{formula}"></span>. '
                        "Если урав­не­ние имеет более од­но­го корня, ука­жи­те "
                        f"{kind} из них.</p>"
                    ),
                },
                {"key": "answer", "section_id": "answer:1", "html": f"<p>{answer}</p>"},
            ],
        }
    }


def _solution(plan) -> str:
    return next(item["value"]["html"] for item in plan.transformations if item["transformation_target_id"] == "section:solution")


def _shifted_context(formula: str, *, kind: str) -> dict:
    return {
        "normalized_content": {
            "format": "teacherhelper-normalized",
            "schema_version": 3,
            "assets": [],
            "sections": [
                {
                    "key": "condition",
                    "section_id": "condition:1",
                    "asset_keys": [],
                    "html": (
                        '<p>Най­ди­те ко­рень урав­не­ния '
                        f'<span data-inline-latex="{formula}"></span>. '
                        "Если урав­не­ние имеет более од­но­го корня, в от­ве­те ука­жи­те "
                        f"{kind} из них.</p>"
                    ),
                },
                {"key": "answer", "section_id": "answer:1", "html": "<p></p>"},
            ],
        }
    }


def _transposed_context(formula: str, *, kind: str) -> dict:
    return _shifted_context(formula, kind=kind)


def test_parent_layout_has_discriminant_before_one_root_collection() -> None:
    plan = build_repair_plan(_context(r"x^{2}-17x+72=0"), parent_condition_asset_id=None)

    assert plan.answer == "8"
    html = _solution(plan)
    assert "фор­му­лой дис­кри­ми­нан­та" in html
    assert r"D=b^2-4ac=(-17)^{2}-4\cdot1\cdot72=1" in html
    assert r"\sqrt{289-288}" in html
    assert html.count(r"\left[\begin{aligned}") == 2


@pytest.mark.parametrize(
    ("formula", "kind", "expected"),
    [
        (r"x^{2}-x-72=0", "меньший", "-8"),
        (r"x^{2}-36=0", "меньший", "-6"),
        (r"x^{2}+4x=0", "меньший", "-4"),
        (r"2x^{2}-33x+136=0", "больший", "8,5"),
    ],
)
def test_accepted_canonical_forms_compute_requested_root(formula: str, kind: str, expected: str) -> None:
    assert build_repair_plan(_context(formula, kind=kind), parent_condition_asset_id="").answer == expected


@pytest.mark.parametrize(
    ("intro", "formula", "selection", "expected"),
    [
        ("Най­ди­те ко­рень урав­не­ния", r"x^{2}+10x+21=0", "меньший", "-7"),
        ("Ре­ши­те урав­не­ние", r"x^{2}+4x-45=0", "меньший", "-9"),
        ("Ре­ши­те урав­не­ние:", r"x^{2}+3x-18=0", "больший", "3"),
    ],
)
def test_standard_quadratics_accept_catalog_wording_variants(
    intro: str, formula: str, selection: str, expected: str
) -> None:
    context = _context(formula, kind=selection)
    context["normalized_content"]["sections"][0]["html"] = (
        f'<p>{intro} <span data-inline-latex="{formula}"></span>.</p>'
        "<p>Если урав­не­ние имеет более од­но­го корня, в от­ве­те ука­жи­те "
        f"{selection} из них.</p>"
    )

    assert build_repair_plan(context, parent_condition_asset_id=None).answer == expected


def test_named_sign_root_request_remains_fail_closed() -> None:
    context = _context(r"x^{2}-x-6=0", kind="меньший")
    context["normalized_content"]["sections"][0]["html"] = (
        '<p>Най­ди­те от­ри­ца­тель­ный ко­рень урав­не­ния '
        '<span data-inline-latex="x^{2}-x-6=0"></span>.</p>'
    )

    with pytest.raises(RightTrianglePlanError, match="condition does not match"):
        build_repair_plan(context, parent_condition_asset_id=None)


@pytest.mark.parametrize(
    ("formula", "intro", "selection", "expected", "normalized"),
    [
        (r"x^{2}=7x+8", "Най­ди­те ко­рень урав­не­ния", "меньший", "-1", r"x^{2}-7x-8=0"),
        (r"x^{2}=17x-72", "Ре­ши­те урав­не­ние", "больший", "9", r"x^{2}-17x+72=0"),
        (r"x^{2}=-2x+24", "Ре­ши­те урав­не­ние", "больший", "4", r"x^{2}+2x-24=0"),
        (r"x^{2}=-x+20", "Ре­ши­те урав­не­ние", "больший", "4", r"x^{2}+x-20=0"),
    ],
)
def test_right_affine_quadratics_are_normalized_before_discriminant(
    formula: str, intro: str, selection: str, expected: str, normalized: str
) -> None:
    context = _context(formula, kind=selection)
    verb = "за­пи­ши­те" if formula == r"x^{2}=17x-72" else "ука­жи­те"
    quantifier = "боль­ше" if formula == r"x^{2}=17x-72" else "более"
    context["normalized_content"]["sections"][0]["html"] = (
        f'<p>{intro} <span data-inline-latex="{formula}"></span>.</p>'
        f"<p>Если урав­не­ние имеет {quantifier} од­но­го корня, в от­ве­те {verb} "
        f"{selection} из них.</p>"
    )

    plan = build_repair_plan(context, parent_condition_asset_id=None)

    assert plan.answer == expected
    assert f"{formula}\\iff {normalized}" in _solution(plan)


@pytest.mark.parametrize(
    ("formula", "kind", "expected", "normalized"),
    [
        (r"x^{2}+10x=-16", "меньший", "-8", r"x^{2}+10x+16=0"),
        (r"x^{2}+11x=-28", "больший", "-4", r"x^{2}+11x+28=0"),
        (r"x^{2}-9x=-20", "больший", "5", r"x^{2}-9x+20=0"),
    ],
)
def test_shifted_quadratics_select_the_requested_root(
    formula: str, kind: str, expected: str, normalized: str
) -> None:
    plan = build_repair_plan(_shifted_context(formula, kind=kind), parent_condition_asset_id=None)

    assert plan.answer == expected
    solution = _solution(plan)
    assert f"{formula}\\iff {normalized}" in solution
    assert solution.index(f"{formula}\\iff {normalized}") < solution.index("D=b^2-4ac")


@pytest.mark.parametrize(
    ("formula", "kind", "expected", "normalized"),
    [
        (r"x^{2}+12=7x", "меньший", "3", r"x^{2}-7x+12=0"),
        (r"x^{2}+10=7x", "больший", "5", r"x^{2}-7x+10=0"),
        (r"x^{2}+8=6x", "больший", "4", r"x^{2}-6x+8=0"),
    ],
)
def test_transposed_quadratics_select_the_requested_root(
    formula: str, kind: str, expected: str, normalized: str
) -> None:
    plan = build_repair_plan(_transposed_context(formula, kind=kind), parent_condition_asset_id=None)

    assert plan.answer == expected
    solution = _solution(plan)
    assert f"{formula}\\iff {normalized}" in solution
    assert solution.index(f"{formula}\\iff {normalized}") < solution.index("D=b^2-4ac")


def test_non_square_discriminant_fails_closed() -> None:
    with pytest.raises(RightTrianglePlanError, match="discriminant"):
        build_repair_plan(_context(r"x^{2}+x-1=0"), parent_condition_asset_id=None)


def test_unexpected_asset_fails_closed() -> None:
    context = deepcopy(_context(r"x^{2}-36=0"))
    context["normalized_content"]["assets"].append({"asset_key": "image_1"})
    with pytest.raises(RightTrianglePlanError):
        build_repair_plan(context, parent_condition_asset_id=None)


def test_base_ege_group_26667_reuses_the_quadratic_selector() -> None:
    profile = get_group_profile("ege-base-26667")

    assert profile.source_group_id == "13690f80-628b-4848-b826-390378fb680a"
    assert profile.content_rule_key == "elementary-equations-26667-quadratic-root-selector"


def test_base_ege_group_506430_reuses_the_quadratic_selector() -> None:
    profile = get_group_profile("ege-base-506430")

    assert profile.source_group_id == "b1e4fe19-45b1-4959-a4d0-7dc1cc349a70"
    assert profile.content_rule_key == "elementary-equations-26667-quadratic-root-selector"
