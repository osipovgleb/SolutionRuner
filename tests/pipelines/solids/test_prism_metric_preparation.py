"""Verify original metric questions, proofs, replay and unsupported geometric cases."""

from copy import deepcopy

import pytest
from midpoint_source_cases import replay, section
from prism_metric_oracle import verify
from prism_metric_source_cases import CASES, GROUPS, arguments, plan, read, saved_answer
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.prism_model import read_question


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_each_geometric_equality_and_stable_replay(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
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
def test_parent_pins_and_profile(group, field):
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
    profile = get_group_profile(group)
    handler = get_handler(GROUPS[group]["rule"])
    assert profile.group_order_index == GROUPS[group]["order_index"]
    assert profile.source_group_id == GROUPS[group]["group_uuid"]
    assert (
        handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )


@pytest.mark.parametrize(
    "text",
    [
        "В правильной шестиугольной призме ABCDEFA_1B_1C_1D_1E_1F_1 все ребра равны 0. Найдите расстояние между точками A и D.",
        "В правильной шестиугольной призме ABCDEFA_1B_1C_1D_1E_1F_1 все ребра равны 2. Найдите расстояние между точками A и B.",
        "В правильной треугольной призме ABCA_1B_1C_1 все ребра равны 2. Найдите расстояние между точками A и B.",
        "В правильной шестиугольной призме ABCDEFA_1B_1C_1D_1E_1F_1 все ребра равны 2. Найдите угол между прямыми AB и DE. Ответ дайте в градусах.",
        "В правильной четырехугольной призме ABCDA_1B_1C_1D_1 известно, что AC_1=2AA_1. Найдите угол между диагоналями BD_1 и CA_1. Ответ дайте в градусах.",
        "В кубе ABCDA_1B_1C_1D_1 найдите угол между прямыми AB и CD. Ответ дайте в градусах.",
        "В правильной шестиугольной призме ABCDEFA_1B_1C_1D_1E_1F_1 все ребра равны 2. Найдите тангенс угла AB_1B.",
        "В правильной шестиугольной призме ABCDEFA_1B_1C_1D_1E_1F_1 все ребра равны 2. Найдите угол AC_1C. Ответ дайте в градусах. Округлите до сотых.",
    ],
)
def test_unreviewed_incomplete_or_degenerate_questions_fail_closed(text):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + text + "</p>")


def test_exact_new_edge_is_computed_without_answer_lookup():
    m = read_question(
        r"<p>В правильной шестиугольной призме ABCDEFA_1B_1C_1D_1E_1F_1 все ребра равны 3\sqrt{5}. Найдите расстояние между точками A и D_1.</p>"
    )
    assert m.answer == 15
