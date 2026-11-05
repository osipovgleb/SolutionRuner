"""Check native prism targets, geometric equalities, parent pins and exact general inputs."""

from copy import deepcopy

import pytest
import sympy as sp
from midpoint_source_cases import replay, section
from prism_formula_oracle import verify
from prism_source_cases import CASES, GROUPS, arguments, plan, read, saved_answer
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.prism_model import read_question


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answer_each_equality_and_immutable_inputs(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    m = read(case)
    result = plan(case, ctx)
    assert (
        ctx == before
        and PiParser(result.answer).parse().value
        == PiParser(saved_answer(case)).parse().value
    )
    verify(result, m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    if section(before, "condition")["asset_keys"]:
        assert section(ctx, "condition") == section(before, "condition")
    assert {a["asset_id"] for a in before["normalized_content"]["assets"]} <= {
        a["asset_id"] for a in ctx["normalized_content"]["assets"]
    }


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_full_reviewed_parent_pins_and_profiles(group, field):
    c = next(c for c in CASES if c["task"] == group)
    args = arguments(group)
    override = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Другой метод.</p>"}
        if field == "html"
        else {"parent_asset_id": "foreign"}
        if field == "primary"
        else {"parent_solution_assets": ({"asset_key": "foreign"},)}
    )
    with pytest.raises(ContentPlanError):
        plan(c, **override)
    p = get_group_profile(group)
    h = get_handler(GROUPS[group]["rule"])
    h.validate()
    assert (
        p.group_order_index == GROUPS[group]["order_index"]
        and p.source_group_id == GROUPS[group]["group_uuid"]
    )
    assert (
        h.requires_frozen_manifest
        and h.strict_frozen_input
        and h.verify_content_readback
    )


@pytest.mark.parametrize("group", GROUPS)
def test_unknown_instruction_fails_closed(group):
    c = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(c["context"])
    section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "Основанием прямой треугольной призмы служит прямоугольный треугольник с катетами 1.5 и 2.5, боковое ребро равно 4. Найдите объем призмы.",
            sp.Rational(15, 2),
        ),
        (
            r"Найдите объем правильной шестиугольной призмы, стороны основания которой равны 2, а боковые ребра равны 3\sqrt{0{,}75}.",
            27,
        ),
        (
            "Найдите боковое ребро правильной четырехугольной призмы, если сторона ее основания равна 2, а площадь поверхности равна 24.",
            2,
        ),
        (
            "Гранью параллелепипеда является ромб со стороной 2 и острым углом 30°. Одно из ребер параллелепипеда составляет с этой гранью угол в 60° и равно 4. Найдите объем параллелепипеда.",
            4 * sp.sqrt(3),
        ),
        (
            "Площадь поверхности правильной треугольной призмы равна 36. Какой будет площадь поверхности призмы, если все ее ребра уменьшить в три раза?",
            4,
        ),
    ],
)
def test_general_exact_inputs_and_independent_angles(text, expected):
    assert sp.simplify(read_question("<p>" + text + "</p>").answer - expected) == 0


@pytest.mark.parametrize(
    "text",
    [
        (
            "Найдите боковое ребро правильной четырехугольной призмы, если сторона ее основания равна 2, а площадь поверхности равна 8."
        ),
        (
            "Найдите боковое ребро правильной четырехугольной призмы, если сторона ее основания равна 2, а площадь поверхности равна 6."
        ),
        (
            "Основанием прямой треугольной призмы служит прямоугольный треугольник с катетами 0 и 2, боковое ребро равно 4. Найдите объем призмы."
        ),
        (
            "Основанием треугольной призмы служит прямоугольный треугольник с катетами 2 и 3, боковое ребро равно 4. Найдите объем призмы."
        ),
        (
            "Найдите объем правильной шестиугольной призмы, стороны основания которой равны 2, а боковые ребра равны -3."
        ),
    ],
)
def test_nonphysical_and_insufficient_conditions_fail_closed(text):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + text + "</p>")


def test_different_face_and_edge_angles_drive_the_complete_oblique_proof():
    from bs4 import BeautifulSoup

    c = next(c for c in CASES if c["task"] == "27104")
    ctx = deepcopy(c["context"])
    s = section(ctx, "condition")
    picture = str(BeautifulSoup(s["html"], "html.parser").img)
    s["html"] = (
        "<p>"
        + picture
        + "Гранью параллелепипеда является ромб со стороной 2 и острым углом 30°. Одно из ребер параллелепипеда составляет с этой гранью угол в 60° и равно 4. Найдите объем параллелепипеда.</p>"
    )
    result = plan(c, ctx)
    m = read({**c, "context": ctx})
    assert PiParser(result.answer).parse().value == 4 * sp.sqrt(3)
    verify(result, m)
    replay(ctx, result.transformations)
    assert plan(c, ctx).transformations == ()
