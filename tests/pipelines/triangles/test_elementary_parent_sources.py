"""Area constraints and angle sums independently audit every elementary proof step."""

import gzip
import hashlib
import re
from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from elementary_source_cases import (
    CASES,
    DATA,
    parent_html,
    plan,
    section,
    solution_html,
)

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.right import elementary_parent

PARAMETERS = {
    "27617": (6, 10),
    "56455": (36, 39),
    "56457": (36, 45),
    "56459": (18, 30),
    "27618": (24, 2),
    "56505": (60, 2),
    "56507": (2, 3),
    "56509": (104, 3),
    "27742": (32,),
    "509598": (38,),
    "689053": (6,),
    "45947": (6,),
    "27753": (4,),
    "46755": (sp.Rational(19, 11),),
    "46757": (sp.Rational(8, 7),),
    "46759": (sp.Rational(41, 4),),
}


@cache
def oracle(group, task):
    p = PARAMETERS[task]
    x, y = sp.symbols("x y", positive=True)
    if group == "27617":
        roots = sp.solve((x - p[0], x * x + y * y - p[1] ** 2), (x, y), dict=True)
        assert len(roots) == 1
        return roots[0][x] * roots[0][y] / 2, {
            "a": roots[0][y],
            "S": roots[0][x] * roots[0][y] / 2,
        }
    if group == "27618":
        roots = sp.solve((x * y - 2 * p[0], y - x - p[1]), (x, y), dict=True)
        assert len(roots) == 1
        z = sp.Symbol("z", real=True)
        polynomial = z * (z + p[1]) - 2 * p[0]
        solutions = sp.solve(polynomial, z)
        small = roots[0][x]
        negative = next(r for r in solutions if r < 0)
        return small, {
            "x": small,
            "x_1": small,
            "x_2": negative,
            "D": sp.discriminant(polynomial, z),
        }
    if group == "27742":
        roots = sp.solve((x + y - 90, x - y - p[0]), (x, y), dict=True)
        assert len(roots) == 1
        return roots[0][x], {"A": roots[0][x], "B": roots[0][y]}
    roots = sp.solve((x + y - 90, y - p[0] * x), (x, y), dict=True)
    assert len(roots) == 1
    return roots[0][y], {"x": roots[0][x]}


def statements(text):
    text = text.replace(r"\begin{cases}", "").replace(r"\end{cases}", "")
    text = text.replace(r"^{\circ}", "").replace(r"^\circ", "")
    return re.split(r"\\\\|\\iff", text)


def numeric(text, values):
    pattern = r"x_[12]|\\angle\s*[AB]|(?<![A-Za-z])(?:D|a|S|x)(?![A-Za-z_])"
    return re.sub(
        pattern,
        lambda m: "(" + sp.latex(values[m[0].replace(r"\angle", "").strip()]) + ")",
        text,
    )


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_existing_group_reuses_its_rule_with_parent_review_and_solution_rewrite(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["group_uuid"] and group["group_size"] >= 3
    assert (
        profile.existing_solution_policy == "rewrite"
        and profile.content_rule_key == group["rule"]
    )
    assert ("parent_solution_html", "parent_solution_html") in get_handler(
        group["rule"]
    ).inputs


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answer_and_every_proof_equality_follow_independent_constraints(case):
    answer, values = oracle(case["group"], case["task"])
    result = plan(case)
    assert sp.Rational(result.answer.replace(",", ".")) == answer
    saved = (
        BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
        .get_text("", strip=True)
        .removesuffix(".")
    )
    assert sp.Rational(saved.replace(",", ".")) == answer
    for node in BeautifulSoup(solution_html(result), "html.parser").select(
        "[data-inline-latex]"
    ):
        for statement in statements(node["data-inline-latex"]):
            parts = statement.split("=")
            assert len(parts) >= 2
            numbers = [
                TrigonometricParser(numeric(p, values)).parse().value for p in parts
            ]
            assert all(sp.simplify(n - numbers[0]) == 0 for n in numbers), (
                case["task"],
                statement,
            )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_stale_answers_and_solutions_do_not_drive_planning_and_replay_is_empty(case):
    context = deepcopy(case["context"])
    for key in ("answer", "solution"):
        section(context, key)["html"] = "<p>Не использовать 999.</p>"
    original = deepcopy(context)
    result = plan(case, context)
    assert context == original and result.answer == plan(case).answer
    for change in result.transformations:
        target = change["transformation_target_id"]
        assert not target.startswith(("section:condition", "asset:"))
        next(
            s
            for s in context["normalized_content"]["sections"]
            if s["transformation_target_id"] == target
        ).update(change["value"])
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize("group", ["27617", "27618", "27742", "27753"])
@pytest.mark.parametrize("change", ["formula", "extra_method"])
def test_unreviewed_parent_changes_do_not_get_partial_or_guessed_solutions(
    group, change
):
    case = next(c for c in CASES if c["group"] == group)
    soup = BeautifulSoup(parent_html(group), "html.parser")
    if change == "formula":
        soup.select_one("[data-inline-latex]")["data-inline-latex"] = "x=999"
    else:
        soup.append(
            BeautifulSoup('<span data-inline-latex="x=999"></span>', "html.parser")
        )
    with pytest.raises(ContentPlanError):
        plan(case, parent=str(soup))


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["task"] == c["group"]], ids=lambda c: c["task"]
)
def test_additional_condition_instructions_are_not_discarded(case):
    context = deepcopy(case["context"])
    section(context, "condition")["html"] += "<p>Удвойте ответ.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, context)


@pytest.mark.parametrize("task", ["27618", "56505", "56507", "56509"])
def test_both_quadratic_roots_are_shown_and_negative_length_is_rejected(task):
    case = next(c for c in CASES if c["task"] == task)
    html = solution_html(plan(case))
    assert (
        "x_1=" in html and "x_2=" in html and "Отрицательный корень не подходит" in html
    )


def test_reviewed_qualitative_figure_is_preserved_byte_for_byte():
    for source, digest in elementary_parent._SOURCES.items():
        p = Path(elementary_parent.__file__).with_name("assets") / (source + ".svgz")
        assert hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest() == digest


@pytest.mark.parametrize(
    "group,html",
    [
        (
            "27617",
            "<p>Найдите площадь прямоугольного треугольника, если его катет и гипотенуза равны соответственно 6 и 4.</p>",
        ),
        (
            "27618",
            "<p>Площадь прямоугольного треугольника равна 24. Один из его катетов на 0 больше другого. Найдите меньший катет.</p>",
        ),
        (
            "27742",
            "<p>Один острый угол прямоугольного треугольника на 90° больше другого. Найдите больший острый угол. Ответ дайте в градусах.</p>",
        ),
        (
            "27753",
            "<p>Один острый угол прямоугольного треугольника в 1 раза больше другого. Найдите больший острый угол. Ответ дайте в градусах.</p>",
        ),
    ],
)
def test_impossible_lengths_and_nonacute_or_equal_angle_relations_are_rejected(
    group, html
):
    case = next(c for c in CASES if c["group"] == group)
    context = deepcopy(case["context"])
    section(context, "condition")["html"] = html
    before = deepcopy(context)
    with pytest.raises(ContentPlanError):
        plan(case, context)
    assert context == before


@pytest.mark.parametrize("group", ["27617", "27618", "27742", "27753"])
def test_registered_parent_mode_does_not_fall_back_when_parent_method_is_missing(group):
    case = next(c for c in CASES if c["group"] == group)
    with pytest.raises(ContentPlanError):
        plan(case, parent="")
