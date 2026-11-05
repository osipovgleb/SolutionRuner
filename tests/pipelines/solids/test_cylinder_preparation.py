"""Check native answers, independent physical formulas and general cylinder questions."""

from copy import deepcopy

import pytest
import sympy as sp
from cylinder_formula_oracle import verify
from cylinder_source_cases import CASES, GROUPS, arguments, plan, read, saved_answer
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_answer_equality_immutable_input_source_ids_and_empty_replay(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    m = read(case)
    result = plan(case, ctx)
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
    if section(before, "condition")["asset_keys"]:
        assert section(ctx, "condition") == section(before, "condition")
    assert {a["asset_id"] for a in before["normalized_content"]["assets"]} <= {
        a["asset_id"] for a in ctx["normalized_content"]["assets"]
    }


def test_changed_dimensions_and_input_kind_follow_actual_child_condition():
    ratios = next(c for c in CASES if c["task"] == "630090")
    m = read(ratios)
    assert m.given == (6, sp.Rational(1, 2), 3) and m.answer == 27
    diameter = next(c for c in CASES if c["task"] == "927")
    m = read(diameter)
    assert m.kind == "diameter" and m.answer == 7
    assert "\\pi d" in solution_html(plan(diameter))


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_full_parent_pins_and_strict_registered_profile(group, field):
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
        profile.group_order_index == GROUPS[group]["order_index"]
        and profile.source_group_id == GROUPS[group]["group_uuid"]
    )
    assert (
        handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )
    assert handler.requires_parent_condition_asset == (group != "27053")


@pytest.mark.parametrize(
    "kh,kr",
    [
        (2, 3),
        (sp.Rational(1, 2), 3),
        (3, sp.Rational(1, 2)),
        (sp.Rational(1, 2), sp.Rational(1, 3)),
    ],
)
def test_volume_scaling_covers_independent_radius_and_height_changes(kh, kr):
    case = next(c for c in CASES if c["task"] == "27053")
    ctx = deepcopy(case["context"])

    def words(k):
        return str(k if k > 1 else 1 / k) + " раза " + ("больше" if k > 1 else "меньше")

    section(ctx, "condition")["html"] = (
        "<p>Объем первого цилиндра равен 10 м<sup>3</sup>. У второго цилиндра высота в "
        + words(kh)
        + ", а радиус основания в "
        + words(kr)
        + ", чем у первого. Найдите объем второго цилиндра. Ответ дайте в кубических метрах.</p>"
    )
    m = read({**case, "context": ctx})
    assert sp.simplify(m.answer - 10 * kh * kr * kr) == 0
    result = plan(case, ctx)
    verify(result, m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "group,text",
    [
        (
            "27046",
            "В цилиндрическом сосуде уровень жидкости достигает 12 см. На какой высоте будет находиться уровень жидкости, если ее перелить во второй сосуд, диаметр которого в 2 раза меньше первого? Ответ дайте в сантиметрах.",
        ),
        (
            "27058",
            r"Радиус основания цилиндра равен \sqrt{2}, высота равна 1,5. Найдите площадь боковой поверхности цилиндра, деленную на \pi.",
        ),
        (
            "27133",
            "Длина окружности основания цилиндра равна 1,5, высота равна 2,5. Найдите площадь боковой поверхности цилиндра.",
        ),
        (
            "245358",
            r"Длина окружности основания цилиндра равна 3\pi. Площадь боковой поверхности равна 12\pi. Найдите высоту цилиндра.",
        ),
        (
            "284361",
            r"Площадь боковой поверхности цилиндра равна 3\pi, а диаметр основания равен 2. Найдите высоту цилиндра.",
        ),
        (
            "284362",
            r"Площадь боковой поверхности цилиндра равна 3\pi, а высота равна 2. Найдите диаметр основания.",
        ),
    ],
)
def test_general_positive_exact_quantities(group, text):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    ctx["normalized_content"]["assets"] = []
    for s in ctx["normalized_content"]["sections"]:
        if s["key"] == "solution":
            s["html"] = "<p>Старое решение.</p>"
            s["asset_keys"] = []
    section(ctx, "condition")["html"] = "<p>" + text + "</p>"
    section(ctx, "condition")["asset_keys"] = []
    result = plan(case, ctx)
    verify(result, read({**case, "context": ctx}))
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "replacement",
    [
        ("12", "0"),
        ("12", "-2"),
        ("м<sup>3</sup>", "м<sup>2</sup>"),
        ("м<sup>3</sup>", 'м<sup class="x">3</sup>'),
        ("в три раза", "в один раза"),
    ],
)
def test_nonphysical_or_ambiguous_dimensions_and_typed_units_fail_closed(replacement):
    case = next(c for c in CASES if c["task"] == "27053")
    ctx = deepcopy(case["context"])
    s = section(ctx, "condition")
    s["html"] = s["html"].replace(*replacement)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", GROUPS)
def test_unknown_instructions_rejected(group):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_displacement_requires_explicit_full_immersion_and_matching_units():
    case = CASES[0]
    for old, new in [
        ("полностью ", ""),
        ("см<sup>3</sup>", "м<sup>3</sup>"),
        ("в см<sup>3</sup>.", "в литрах."),
    ]:
        ctx = deepcopy(case["context"])
        original = section(ctx, "condition")["html"].replace("\xad", "")
        assert old in original
        section(ctx, "condition")["html"] = original.replace(old, new)
        with pytest.raises(ContentPlanError):
            plan(case, ctx)
