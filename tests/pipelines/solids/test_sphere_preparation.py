"""Check all seven source families, exact formulae and structurally different children."""

from copy import deepcopy

import pytest
import sympy as sp
from midpoint_source_cases import replay, section, solution_html
from sphere_formula_oracle import verify
from sphere_source_cases import CASES, GROUPS, arguments, plan, read, saved_answer

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_answers_every_equality_source_immutability_and_empty_replay(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    m = read(case)
    assert (
        ctx == before
        and sp.simplify(
            ScalarParser(result.answer).parse()
            - ScalarParser(saved_answer(case)).parse()
        )
        == 0
    )
    verify(result, m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    old = section(before, "condition")
    new = section(ctx, "condition")
    if old["asset_keys"]:
        assert old == new
    assert {a["asset_id"] for a in before["normalized_content"]["assets"]} <= {
        a["asset_id"] for a in ctx["normalized_content"]["assets"]
    }


def test_known_source_errors_are_corrected_from_condition_without_changing_fixture():
    zero = next(c for c in CASES if c["task"] == "75311")
    assert (
        section(zero["context"], "answer")["html"]
        == '<p><span data-effect="spaced">0</span></p>'
    )
    assert plan(zero).answer == "12"
    reversed_case = next(c for c in CASES if c["task"] == "76349")
    m = read(reversed_case)
    assert (m.large, m.small) == (2, 1)
    assert r"\frac{V_2}{V_1}" in solution_html(plan(reversed_case))
    diameter = next(c for c in CASES if c["task"] == "505443")
    m = read(diameter)
    assert m.input_kind == "diameter" and m.answer == 64
    html = solution_html(plan(diameter))
    assert r"\frac{d_2}{d_1}" in html and r"\sqrt[3]" not in html


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_full_parent_pins_and_frozen_profile(group, field):
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
    profile = get_group_profile(group)
    handler = get_handler(GROUPS[group]["rule"])
    handler.validate()
    assert (
        profile.source_group_id == GROUPS[group]["group_uuid"]
        and profile.group_order_index == GROUPS[group]["order_index"]
    )
    assert handler.requires_parent_condition_asset == (group != "27125")
    assert (
        handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )


def test_image_free_parent_accepts_the_runtime_empty_primary_but_not_an_extra_picture():
    case = next(c for c in CASES if c["task"] == "27125")
    assert plan(case, parent_asset_id="").answer == "12"
    with pytest.raises(ContentPlanError):
        plan(case, parent_asset_id="unreviewed")


@pytest.mark.parametrize("kind", ["Радиус", "Диаметр", "Объем"])
@pytest.mark.parametrize(
    "large,small", [("первого", "второго"), ("второго", "первого")]
)
@pytest.mark.parametrize("factor", [2, sp.Rational(3, 2), sp.Integer(27)])
def test_linear_size_and_volume_comparisons_share_correct_power_and_direction(
    kind, large, small, factor
):
    case = next(c for c in CASES if c["task"] == "27072")
    ctx = deepcopy(case["context"])
    img = section(ctx, "condition")["html"].split("/>")[0] + "/>"
    text = (
        f"{kind} {large} шара в {sp.latex(factor)} раза больше "
        + {"Радиус": "радиуса", "Диаметр": "диаметра", "Объем": "объема"}[kind]
        + f" {small}. Во сколько раз площадь поверхности {small} шара меньше площади поверхности {large}?"
    )
    section(ctx, "condition")["html"] = "<p>" + img.removeprefix("<p>") + text + "</p>"
    m = read({**case, "context": ctx})
    result = plan(case, ctx)
    verify(result, m)
    power = 3 if kind == "Объем" else 1
    assert sp.simplify(m.answer**power - factor**2) == 0
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "group,given",
    [
        ("27059", (sp.Rational(7, 3),)),
        ("27097", (sp.Rational(3, 2),)),
        ("27125", (1, 2, 3)),
        ("27163", (1, 2)),
        ("27174", (2,)),
    ],
)
def test_noninteger_answers_remain_exact_and_method_is_general(group, given):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    s = section(ctx, "condition")
    replacements = {
        "27059": ("равна 3.", "равна \\frac{7}{3}."),
        "27097": ("в три раза", "в 1,5 раза"),
        "27125": ("6, 8 и 10", "1, 2 и 3"),
        "27163": ("6 и 8", "1 и 2"),
        "27174": ("288", "2"),
    }
    s["html"] = s["html"].replace(*replacements[group])
    m = read({**case, "context": ctx})
    result = plan(case, ctx)
    verify(result, m)
    if m.mode == "combined_radius":
        assert (
            sp.simplify(
                m.answer**m.degree - sum(sp.sympify(v) ** m.degree for v in given)
            )
            == 0
        )
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("bad", ["-3", "0", "1 2", "12 34", "1 0000"])
def test_negative_zero_and_ambiguous_digit_groups_fail_closed(bad):
    case = next(c for c in CASES if c["task"] == "27174")
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        "288", bad
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", GROUPS)
def test_unknown_instruction_or_other_family_is_rejected(group):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "text",
    [
        "Радиус первого шара в 1 раза больше радиуса второго. Во сколько раз площадь поверхности первого шара больше площади поверхности второго?",
        "Радиус первого шара в 2 раза больше диаметра второго. Во сколько раз площадь поверхности первого шара больше площади поверхности второго?",
        "Радиус первого шара в 2 раза больше радиуса второго. Во сколько раз площадь поверхности второго шара больше площади поверхности первого?",
        "Радиус первого шара в 2 раза больше радиуса первого. Во сколько раз площадь поверхности первого шара больше площади поверхности второго?",
    ],
)
def test_contradictory_comparisons_fail_closed(text):
    case = next(c for c in CASES if c["task"] == "27072")
    ctx = deepcopy(case["context"])
    ctx["normalized_content"]["assets"] = []
    s = section(ctx, "condition")
    s["html"] = "<p>" + text + "</p>"
    s["asset_keys"] = []
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
