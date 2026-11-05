"""Check actual native cone answers, complete proofs and general physical dimensions."""

from copy import deepcopy

import pytest
import sympy as sp
from cone_formula_oracle import verify
from cone_source_cases import CASES, GROUPS, arguments, plan, read, saved_answer
from midpoint_source_cases import replay, section
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.cone_model import read_question


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_and_every_equality_without_saved_answer_lookup(case):
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
def test_strict_parent_pins_and_profiles(group, field):
    case = next(c for c in CASES if c["task"] == group)
    args = arguments(group)
    override = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Другой метод.</p>"}
        if field == "html"
        else {"parent_asset_id": "foreign"}
        if field == "primary"
        else {"parent_solution_assets": ({"asset_key": "foreign"},)}
    )
    with pytest.raises(ContentPlanError):
        plan(case, **override)
    p = get_group_profile(group)
    handler = get_handler(GROUPS[group]["rule"])
    handler.validate()
    assert (
        p.group_order_index == GROUPS[group]["order_index"]
        and p.source_group_id == GROUPS[group]["group_uuid"]
    )
    assert (
        handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )


@pytest.mark.parametrize("group", GROUPS)
def test_added_instruction_fails_closed(group):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            r"Высота конуса равна 1,5, образующая равна 2,5. Найдите его объем, деленный на \pi.",
            2,
        ),
        (
            r"Высота конуса равна 1.5, образующая равна 2.5. Найдите его объем, деленный на \pi.",
            2,
        ),
        (
            r"Высота конуса равна 3, а длина образующей — 5. Найдите диаметр основания конуса.",
            8,
        ),
        (
            r"Радиус основания конуса равен 1,5, высота равна 2. Найдите площадь полной поверхности конуса, деленную на \pi.",
            6,
        ),
        (
            r"Длина окружности основания конуса равна 3\pi, образующая равна 2,5. Найдите площадь боковой поверхности конуса.",
            sp.Rational(15, 4) * sp.pi,
        ),
        (
            "Во сколько раз увеличится объем конуса, если радиус его основания увеличится в 2,5 раза, а высота останется прежней?",
            sp.Rational(25, 4),
        ),
        (
            "Площадь основания конуса равна 45. Плоскость, параллельная плоскости основания конуса, делит его высоту на отрезки длиной 2 и 4, считая от вершины. Найдите площадь сечения конуса этой плоскостью.",
            5,
        ),
        (
            "Площадь полной поверхности конуса равна 100. Параллельно основанию конуса проведено сечение, делящее высоту в отношении 2:3, считая от вершины конуса. Найдите площадь полной поверхности отсеченного конуса.",
            16,
        ),
    ],
)
def test_general_exact_dimensions_and_oriented_similarity(text, expected):
    m = read_question("<p>" + text + "</p>")
    assert m.answer == expected


@pytest.mark.parametrize(
    "text",
    [
        r"Высота конуса равна 5, образующая равна 3. Найдите его объем, деленный на \pi.",
        r"Высота конуса равна 3, образующая равна 3. Найдите его объем, деленный на \pi.",
        r"Высота конуса равна 0, образующая равна 3. Найдите его объем, деленный на \pi.",
        r"Диаметр основания конуса равен 10, а длина образующей — 4. Найдите высоту конуса.",
        "Длина окружности основания конуса равна 100, образующая равна 1. Найдите площадь боковой поверхности конуса.",
        "Во сколько раз уменьшится объем конуса, если радиус его основания увеличится в 2 раза, а высота останется прежней?",
        "Во сколько раз увеличится объем конуса, если радиус его основания увеличится в 1 раза, а высота останется прежней?",
    ],
)
def test_nonphysical_or_conflicting_conditions_fail_closed(text):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + text + "</p>")


def test_group_lateral_child_volume_uses_actual_target():
    c = next(c for c in CASES if c["task"] == "630177")
    m = read(c)
    assert (
        m.mode == "scale"
        and m.kind == "volume"
        and m.input_kind == "height"
        and m.answer == 9
    )


@pytest.mark.parametrize(
    "text",
    [
        r"Длина окружности основания конуса равна 3, образующая равна 2. Найдите его объем, деленный на \pi.",
        "Высота конуса равна 3, образующая равна 5. Найдите высоту конуса.",
        r"Площадь основания конуса равна 9\pi, высота — 4. Найдите площадь полной поверхности конуса, деленную на \pi.",
    ],
)
def test_unreviewed_input_target_combinations_fail_closed(text):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + text + "</p>")
