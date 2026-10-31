"""All mixed graphs compute from inspected figures, preserve parent methods and A/B."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_profile_hyperbolas import plan as shared_plan
from test_profile_hyperbolas import replay

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational
from solution_runner.pipelines.function_graphs import (
    mixed_models,
    mixed_questions,
    mixed_svg,
)

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_12_mixed.json").read_text()
)
CASES = DATA["cases"]


def plan(case, context=None, *, data=None, mime=None):
    return shared_plan(case, context, data=data, mime=mime or case["condition_mime"])


def changed(case, edit):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = edit(condition["html"])
    return context


def analysis(case):
    question = mixed_questions.parse(case["context"])
    entry, marked = mixed_svg.read(
        case["context"],
        (ROOT / case["condition_file"]).read_bytes(),
        case["condition_mime"],
        question.curve_kind,
    )
    return mixed_models.analyze(question, entry, marked)


def solution(result):
    return BeautifulSoup(
        next(
            t["value"]["html"]
            for t in result.transformations
            if t["transformation_target_id"] == "section:solution:1"
        ),
        "html.parser",
    )


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_all_nine_profiles_share_one_mixed_handler(group):
    p = get_group_profile(group["key"])
    assert p.content_rule_key == "mixed-function-intersection"
    assert (
        p.source_group_id == group["uuid"]
        and p.snapshot_theme_id == group["theme_uuid"]
    )
    assert p.group_order_index == group["order"] and p.theme_order_index == 6
    assert (
        p.category_key == "12"
        and p.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_source_is_computed_without_saved_answer_and_preserves_figures(case):
    old = deepcopy(case["context"])
    result = plan(case)
    saved = next(
        s["html"] for s in old["normalized_content"]["sections"] if s["key"] == "answer"
    )
    assert parse_rational(result.answer) == parse_rational(
        BeautifulSoup(saved, "html.parser").get_text()
    )
    context = deepcopy(old)
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>999999999</p>"
    altered = plan(case, context)
    assert altered.answer == result.answer and solution(altered) == solution(result)
    assert case["context"] == old
    updated = replay(old, result.transformations)
    assert plan(case, updated).transformations == ()
    assert (
        updated["normalized_content"]["assets"] == old["normalized_content"]["assets"]
    )
    assert all(
        s in updated["normalized_content"]["sections"]
        for s in old["normalized_content"]["sections"]
        if s["key"] not in {"answer", "solution"}
    )
    assert {t["transformation_target_id"] for t in result.transformations} <= {
        "section:answer:1",
        "section:solution:1",
    }
    assert (
        hashlib.sha256((ROOT / case["condition_file"]).read_bytes()).hexdigest()
        == case["condition_sha256"]
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_parent_method_and_other_intersection_are_preserved(case):
    a = analysis(case)
    soup = solution(plan(case))
    text = soup.get_text()
    assert len(
        soup.select('section[data-content-kind="solution"]')
    ) == 1 and not soup.select("img")
    forms = [m["data-inline-latex"] for m in soup.select("[data-inline-latex]")]
    assert len(forms) >= 8 and r"\qquadf" not in str(soup)
    if a.question.curve_kind == "parabola":
        assert (
            "Ось симметрии" if a.question.line_origin else "Вычтем значения"
        ) in text
        if a.question.known_line is None and not a.question.line_origin:
            assert "Составим и решим систему" in text
    elif a.question.curve_kind == "reciprocal":
        assert "x ≠ 0" in text and "угловой" in text.lower()
    else:
        assert "неотрицательный квадратный корень" in text and "тангенсу угла" in text
    if a.question.count == 2:
        ax, ay = a.entry["visible_a"]
        assert a.root != ax and a.line.value(ax) == ay
        assert "второй корень относится к B" in text
    assert (
        sp.simplify(a.expression.subs(mixed_models.X, a.root) - a.line.value(a.root))
        == 0
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "edit",
    [
        lambda h: "<p>Дополнительное условие.</p>" + h,
        lambda h: h + '<span data-inline-latex="x=1"></span>',
        lambda h: h + '<img src="extra.svg"/>',
        lambda h: h.replace("f(x)=", "h(x)=", 1),
        lambda h: h.replace('data-asset-key="image_1"', 'data-asset-key="image_2"'),
    ],
)
def test_full_condition_and_canonical_image_are_required(case, edit):
    with pytest.raises(ContentPlanError):
        plan(case, changed(case, edit))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("kind", ["bytes", "mime", "solution_figure"])
def test_unknown_or_foreign_assets_are_rejected(case, kind):
    if kind == "bytes":
        with pytest.raises(ContentPlanError):
            plan(case, data=(ROOT / case["condition_file"]).read_bytes() + b" ")
    elif kind == "mime":
        with pytest.raises(ContentPlanError):
            plan(case, mime="image/jpeg")
    else:
        context = deepcopy(case["context"])
        next(
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "solution"
        )["html"] = '<img src="extra.svg"/>'
        with pytest.raises(ContentPlanError):
            plan(case, context)


@pytest.mark.parametrize(
    "task,expected",
    [
        ("509150", -8),
        ("509151", -3),
        ("509152", -7),
        ("509167", sp.Rational(-1, 5)),
        ("509169", sp.Rational(1, 5)),
        ("642371", sp.Rational(5, 2)),
        ("704626", 6),
        ("677169", 100),
    ],
)
def test_second_intersection_is_not_always_larger_or_positive(task, expected):
    assert analysis(next(c for c in CASES if c["task"] == task)).result == expected


def test_stated_line_must_match_the_original_graph():
    case = CASES[0]
    with pytest.raises(ContentPlanError):
        plan(case, changed(case, lambda h: h.replace("5x+9", "5x+10")))


@pytest.mark.parametrize("task", ["509271", "509272", "509273", "509274"])
def test_negative_square_root_candidate_is_discarded_before_returning_x(task):
    a = analysis(next(c for c in CASES if c["task"] == task))
    assert any(t < 0 for t in a.t_roots)
    assert len(a.roots) == 1 and a.root == next(t * t for t in a.t_roots if t >= 0)
    assert (
        "Отрицательное значение"
        in solution(plan(next(c for c in CASES if c["task"] == task))).get_text()
    )


@pytest.mark.parametrize("kind", ["units", "visible_a", "curve_point"])
def test_inspection_metadata_cannot_override_mathematics(kind, tmp_path, monkeypatch):
    case = CASES[0]
    data = (ROOT / case["condition_file"]).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    entry = json.loads((mixed_svg.ASSET_DIR / "source-evidence.json").read_text())[sha]
    if kind == "units":
        entry["grid_unit"] = [2, 1]
    elif kind == "visible_a":
        entry["visible_a"] = [0, 0]
    else:
        entry["curve_points"][0] = [-2, 5]
    (tmp_path / "source-evidence.json").write_text(json.dumps({sha: entry}))
    monkeypatch.setattr(mixed_svg, "ASSET_DIR", tmp_path)
    with pytest.raises(ContentPlanError):
        plan(case)


@pytest.mark.parametrize("kind", ["origin", "size"])
def test_png_calibration_and_original_ink_are_checked(kind, tmp_path, monkeypatch):
    case = next(c for c in CASES if c["task"] == "704626")
    data = (ROOT / case["condition_file"]).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    entry = json.loads((mixed_svg.ASSET_DIR / "source-evidence.json").read_text())[sha]
    if kind == "origin":
        entry["raster_frame"]["origin"][0] += 10
    else:
        entry["raster_frame"]["size"] = [220, 256]
    (tmp_path / "source-evidence.json").write_text(json.dumps({sha: entry}))
    monkeypatch.setattr(mixed_svg, "ASSET_DIR", tmp_path)
    with pytest.raises(ContentPlanError):
        plan(case)


def test_zero_curve_or_inconsistent_points_do_not_produce_an_answer():
    with pytest.raises(ContentPlanError):
        mixed_models.curve_model(
            "root", [(sp.Integer(0), sp.Integer(0)), (sp.Integer(4), sp.Integer(0))]
        )
    with pytest.raises(ContentPlanError):
        mixed_models.curve_model(
            "reciprocal",
            [(sp.Integer(2), sp.Integer(1)), (sp.Integer(-2), sp.Integer(1))],
        )
