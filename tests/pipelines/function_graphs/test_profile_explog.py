"""All exponential/logarithmic sources, parent methods and independent SVG readings."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_profile_hyperbolas import plan, replay

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational
from solution_runner.pipelines.function_graphs import explog_models as model
from solution_runner.pipelines.function_graphs import (
    explog_questions,
    explog_svg,
    parabola_svg,
)

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_12_explog.json").read_text()
)
CASES = DATA["cases"]


def changed(case, edit):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = edit(condition["html"])
    return context


def analysis(case):
    q = explog_questions.parse(case["context"])
    data = (ROOT / case["condition_file"]).read_bytes()
    entry, points, marked = explog_svg.read(
        case["context"], data, "image/svg+xml", q.model
    )
    return model.analyze(q, points, entry), marked


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
def test_all_eleven_profiles_share_one_graph_handler(group):
    p = get_group_profile(group["key"])
    assert p.content_rule_key == "exponential-logarithmic-function-graph"
    assert (
        p.source_group_id == group["uuid"]
        and p.snapshot_theme_id == group["theme_uuid"]
    )
    assert (
        p.group_order_index == group["order"]
        and p.theme_order_index == group["theme_order"]
    )
    assert (
        p.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
        and p.category_key == "12"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_source_computes_without_saved_answers_or_solutions(case):
    original = deepcopy(case["context"])
    result = plan(case)
    answer = next(
        s["html"]
        for s in original["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    assert parse_rational(result.answer) == parse_rational(
        BeautifulSoup(answer, "html.parser").get_text()
    )
    context = deepcopy(original)
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"solution", "answer"}:
            s["html"] = "<p>999999999</p>"
    assert plan(case, context).answer == result.answer
    assert solution(plan(case, context)) == solution(result)
    assert case["context"] == original
    updated = replay(original, result.transformations)
    assert plan(case, updated).transformations == ()
    assert (
        updated["normalized_content"]["assets"]
        == original["normalized_content"]["assets"]
    )
    assert {t["transformation_target_id"] for t in result.transformations} <= {
        "section:answer:1",
        "section:solution:1",
    }
    assert all(
        s in updated["normalized_content"]["sections"]
        for s in original["normalized_content"]["sections"]
        if s["key"] not in {"answer", "solution"}
    )
    assert (
        hashlib.sha256((ROOT / case["condition_file"]).read_bytes()).hexdigest()
        == case["condition_sha256"]
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_parent_methods_remain_in_order_and_formulas_are_self_contained(case):
    a, _ = analysis(case)
    soup = solution(plan(case))
    methods = soup.select('section[data-content-kind="solution"]')
    two = a.question.model == "exp_vertical" and a.question.mode == "argument"
    assert len(methods) == (2 if two else 1)
    assert not soup.select("img")
    assert all(len(s.select("[data-inline-latex]")) >= 5 for s in methods)
    if two:
        assert methods[1]["data-solution-title"] == "Приведём другое решение."
        assert (
            "Вычтем" in methods[0].get_text()
            and "Множество значений" in methods[1].get_text()
        )
        assert "Проверим формулу по второй точке" in methods[1].get_text()
    if a.question.model == "log_horizontal":
        assert (
            "Область определения" if a.question.mode == "value" else "Вычтем"
        ) in methods[0].get_text()
    if a.question.model == "exp_horizontal":
        assert "нулевом показателе" in methods[0].get_text()
    assert all(
        not f.get("data-inline-latex", "").startswith("Ответ")
        for f in soup.select("[data-inline-latex]")
    )
    assert r"\qquadf" not in str(soup)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "edit",
    [
        lambda h: "<p>Дополнительное условие.</p>" + h,
        lambda h: h + '<span data-inline-latex="x=1"></span>',
        lambda h: h + '<img src="other.svg"/>',
        lambda h: h.replace('data-asset-key="image_1"', 'data-asset-key="image_2"'),
        lambda h: h.replace("f(x)=", "g(x)=", 1),
    ],
)
def test_entire_question_and_canonical_image_are_required(case, edit):
    with pytest.raises(ContentPlanError):
        plan(case, changed(case, edit))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["bytes", "mime", "solution_figure"])
def test_drifted_or_foreign_assets_fail_closed(case, mode):
    if mode == "bytes":
        with pytest.raises(ContentPlanError):
            plan(case, data=(ROOT / case["condition_file"]).read_bytes() + b" ")
    elif mode == "mime":
        with pytest.raises(ContentPlanError):
            plan(case, mime="image/png")
    else:
        context = deepcopy(case["context"])
        next(
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "solution"
        )["html"] = '<p><img src="other.svg"/></p>'
        with pytest.raises(ContentPlanError):
            plan(case, context)


@pytest.mark.parametrize(
    "task,base,shift",
    [
        ("509090", sp.sqrt(2), -3),
        ("509091", sp.sqrt(3), -2),
        ("509092", sp.Rational(1, 2), -4),
        ("509104", sp.sqrt(2), -1),
        ("639749", 2, 0),
        ("660718", sp.Rational(1, 3), 0),
    ],
)
def test_exact_bases_follow_actual_graph_points(task, base, shift):
    a, marked = analysis(next(c for c in CASES if c["task"] == task))
    assert a.base == base and a.shift == shift
    assert all(
        model.function(a.question.model, a.base, a.shift, x) == y for x, y in marked
    )
    if task == "639749":
        assert (sp.Integer(-1), sp.Rational(1, 2)) in marked
    if task == "509090":
        assert (4, 1) in marked
    if task == "509092":
        assert (-3, 4) in marked


@pytest.mark.parametrize(
    "task,target",
    [
        ("509009", "0"),
        ("509042", "-5"),
        ("509095", "-3"),
        ("509101", "0.5"),
        ("509107", "0"),
        ("660992", "3"),
    ],
)
def test_outside_domain_range_or_unrepresentable_exact_answer_is_rejected(task, target):
    case = next(c for c in CASES if c["task"] == task)
    a, _ = analysis(case)
    raw = "f(" + target + ")" if a.question.mode == "value" else "f(x)=" + target
    forms, _ = explog_questions.read(case["context"])
    with pytest.raises(ContentPlanError):
        plan(case, changed(case, lambda h: h.replace(forms[1], raw)))


@pytest.mark.parametrize(
    "model_name,points",
    [
        ("exp_vertical", [(0, 0), (1, 0)]),
        ("log_horizontal", [(0, 0), (0, 1)]),
        ("exp_plain", [(1, -1)]),
        ("log_plain", [(-1, 1)]),
        ("exp_horizontal", [(0, 0), (1, 1)]),
        ("log_vertical", [(0, 0), (1, 1)]),
    ],
)
def test_degenerate_or_invalid_readings_do_not_produce_a_formula(model_name, points):
    with pytest.raises(ContentPlanError):
        model.parameters(model_name, [tuple(map(sp.Rational, p)) for p in points])


def test_ambiguous_positive_base_is_rejected():
    with pytest.raises(ContentPlanError):
        model.positive_base((model.A - 2) * (model.A - 3))


@pytest.mark.parametrize(
    "task,key", [("509042", "vertical_asymptote"), ("509095", "horizontal_asymptote")]
)
def test_asymptote_must_agree_with_independent_point_system(task, key):
    case = next(c for c in CASES if c["task"] == task)
    q = explog_questions.parse(case["context"])
    e, points, _ = explog_svg.read(
        case["context"],
        (ROOT / case["condition_file"]).read_bytes(),
        "image/svg+xml",
        q.model,
    )
    with pytest.raises(ContentPlanError):
        model.analyze(q, points, e | {key: e[key] + 1})


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            "M0,0 C1,2 2,2 3,0 s2,-2 3,0",
            [[[0, 0], [1, 2], [2, 2], [3, 0]], [[3, 0], [4, -2], [5, -2], [6, 0]]],
        ),
        ("M1,1 S2,3 4,5", [[[1, 1], [1, 1], [2, 3], [4, 5]]]),
    ],
)
def test_smooth_svg_cubic_reflects_previous_control_point(raw, expected):
    assert parabola_svg.segments(raw) == expected


@pytest.mark.parametrize("raw", ["M0 0 L1 1", "M0 0 Q1 1 2 2", "M0 0 S1 2", "M0 0 Z"])
def test_uninspected_curve_commands_still_fail_closed(raw):
    with pytest.raises(ContentPlanError):
        parabola_svg.segments(raw)
