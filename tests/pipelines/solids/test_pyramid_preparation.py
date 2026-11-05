"""Verify every reviewed pyramid source, proof, correction, profile and stable replay."""

from copy import deepcopy

import pytest
from midpoint_source_cases import replay, section
from pyramid_formula_oracle import verify
from pyramid_source_cases import CASES, GROUPS, arguments, plan, read, saved_answer
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.pyramid_reader import read as read_question


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answer_geometric_equalities_and_immutable_input(case):
    ctx = deepcopy(case["context"])
    s = section(ctx, "answer")
    if s:
        s["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before
    assert (
        PiParser(result.answer).parse().value
        == PiParser(saved_answer(case)).parse().value
    )
    verify(result, read(case))
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    if section(before, "condition")["asset_keys"]:
        assert section(ctx, "condition") == section(before, "condition")


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_complete_parent_pins_and_actual_profile_indices(group, field):
    c = next(c for c in CASES if c["task"] == group)
    args = arguments(group)
    overrides = {
        "html": {
            "parent_solution_html": args["parent_solution_html"]
            + "<p>Другой метод.</p>"
        },
        "primary": {"parent_asset_id": "foreign"},
        "assets": {"parent_solution_assets": ({"asset_key": "foreign"},)},
    }
    with pytest.raises(ContentPlanError):
        plan(c, **overrides[field])
    p = get_group_profile(group)
    h = get_handler(GROUPS[group]["rule"])
    assert (
        p.group_order_index == GROUPS[group]["order_index"]
        and p.source_group_id == GROUPS[group]["group_uuid"]
    )
    assert (
        h.strict_frozen_input
        and h.requires_frozen_manifest
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
    "text",
    [
        "Во сколько раз увеличится объем пирамиды, если все ее ребра увеличить в 3 раза?",
        "Стороны основания правильной шестиугольной пирамиды равны 10, боковые ребра равны 8. Найдите площадь боковой поверхности этой пирамиды.",
        "Стороны основания правильной четырехугольной пирамиды равны 10, боковые ребра равны 5. Найдите площадь поверхности этой пирамиды.",
        "В правильной четырехугольной пирамиде высота равна 10, боковое ребро равно 10. Найдите ее объем.",
        "Найдите объем правильной треугольной пирамиды, стороны основания которой равны 0, а высота равна 3.",
        "Основанием пирамиды является прямоугольник со сторонами 3 и 4. Ее объем равен -16. Найдите высоту этой пирамиды.",
        "В правильной треугольной пирамиде SABC точка R — середина ребра BC, S — вершина. Известно, что AB=12, а SR=1. Найдите площадь боковой поверхности.",
        "Объем треугольной пирамиды равен 15. Плоскость проходит через сторону основания этой пирамиды и пересекает противоположное боковое ребро в точке, делящей его в отношении 0:2, считая от вершины пирамиды. Найдите больший из объемов пирамид, на которые плоскость разбивает исходную пирамиду.",
    ],
)
def test_nonphysical_conditions_fail_closed(text):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + text + "</p>")
