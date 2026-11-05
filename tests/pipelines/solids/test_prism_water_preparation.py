"""Check visible source clarification, all three methods, transfer reuse and frozen replay."""

import hashlib
import re
from copy import deepcopy
from fractions import Fraction

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from prism_formula_oracle import verify as verify_transfer
from prism_water_source_cases import CASES, GROUPS, arguments, plan, read
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.prism_model import read_question
from solution_runner.pipelines.solids.prism_sources import DATA


def verify_water(result, m):
    v, low, high = (Fraction(str(x)) for x in m.given)
    delta = high - low
    b = v / low
    answer = b * delta
    values = {
        "V_0": v,
        "V_1": b * high,
        "V_d": answer,
        "B": b,
        "h_0": low,
        "h_1": high,
        "k": delta / low,
        r"\Delta h": delta,
    }
    soup = BeautifulSoup(solution_html(result), "html.parser")
    methods = soup.select('section[data-content-kind="solution"]')
    assert [s["data-solution-title"] for s in methods] == [
        "Решение",
        "Альтернативное решение.",
        "Альтернативное решение.",
    ]
    assert len(methods[2].select('ol[data-layout="source-numbered"] > li')) == 3
    for method in methods:
        nodes = method.select("[data-inline-latex]")
        assert len(nodes) == 6
        for node in nodes:
            f = (
                node["data-inline-latex"]
                .replace("kV_0", r"k\cdot V_0")
                .replace("Bh_0", r"B\cdot h_0")
                .replace("Bh_1", r"B\cdot h_1")
            )
            for symbol, amount in sorted(values.items(), key=lambda x: -len(x[0])):
                f = re.sub(
                    r"(?<![A-Za-z_\\])" + re.escape(symbol) + r"(?![A-Za-z_0-9])",
                    lambda _, a=amount: (
                        "(" + str(a.numerator) + "/" + str(a.denominator) + ")"
                    ),
                    f,
                )
            nums = [PiParser(x).parse().value for x in f.split("=")]
            assert len(nums) > 1 and all(x == nums[0] for x in nums), f
    assert PiParser(result.answer).parse().value == answer


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_methods_visible_clarification_and_replay(case):
    ctx = deepcopy(case["context"])
    before = deepcopy(ctx)
    m = read(case)
    result = plan(case, ctx)
    assert ctx == before
    assert (
        result.answer
        == {"27047": "184", "72151": "1755", "522089": "7", "4937": "180"}[case["task"]]
    )
    if m.kind == "transfer":
        verify_transfer(result, m)
    else:
        verify_water(result, m)
    replay(ctx, result.transformations)
    condition = section(ctx, "condition")["html"]
    original = section(before, "condition")["html"]
    if m.kind == "immersion":
        assert condition.replace("полностью ", "", 1) == original
        record = DATA["water_transcriptions"][
            hashlib.sha256(original.encode()).hexdigest()
        ]
        assert (
            hashlib.sha256(condition.encode()).hexdigest() == record["corrected_sha256"]
        )
    else:
        assert condition == original
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert section(ctx, "source") == section(before, "source")
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_complete_parent_pins_and_profile(field):
    args = arguments("27047")
    overrides = {
        "html": {
            "parent_solution_html": args["parent_solution_html"]
            + "<p>Другой метод.</p>"
        },
        "primary": {"parent_asset_id": "foreign"},
        "assets": {"parent_solution_assets": ({"asset_key": "foreign"},)},
    }
    with pytest.raises(ContentPlanError):
        plan(CASES[0], **overrides[field])
    p = get_group_profile("27047")
    h = get_handler(GROUPS["27047"]["rule"])
    assert (
        p.group_order_index == 0 and p.source_group_id == GROUPS["27047"]["group_uuid"]
    )
    assert (
        h.strict_frozen_input
        and h.requires_frozen_manifest
        and h.verify_content_readback
    )


@pytest.mark.parametrize(
    "volume,low,high",
    [
        ("0", "25", "27"),
        ("2300", "0", "27"),
        ("2300", "25", "25"),
        ("2300", "25", "20"),
    ],
)
def test_nonphysical_explicit_conditions_fail_closed(volume, low, high):
    html = (
        "<p>В сосуд, имеющий форму правильной треугольной призмы, налили "
        + volume
        + " см3 воды и полностью погрузили в воду деталь. При этом уровень воды поднялся с отметки "
        + low
        + " см до отметки "
        + high
        + " см. Найдите объем детали. Ответ выразите в см3.</p>"
    )
    with pytest.raises(ContentPlanError):
        read_question(html)


def test_new_explicit_full_immersion_is_computed_and_omitted_qualifier_rejected():
    html = "<p>В сосуд, имеющий форму правильной треугольной призмы, налили 1200 см<sup>3</sup> воды и полностью в нее погрузили деталь. При этом уровень жидкости в сосуде поднялся с отметки 24 см до отметки 26 см. Чему равен объем детали? Ответ выразите в см<sup>3</sup>.</p>"
    assert read_question(html).answer == 100
    with pytest.raises(ContentPlanError):
        read_question(html.replace("полностью ", ""))


def test_changed_unreviewed_raw_condition_does_not_inherit_transcription():
    c = CASES[0]
    ctx = deepcopy(c["context"])
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        "2300", "2350"
    )
    with pytest.raises(ContentPlanError):
        plan(c, ctx)


def test_unknown_instruction_fails_closed_even_for_reviewed_numbers():
    ctx = deepcopy(CASES[0]["context"])
    section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    with pytest.raises(ContentPlanError):
        plan(CASES[0], ctx)


@pytest.mark.parametrize("change", ["foreign", "url", "duplicate"])
def test_source_figure_identity_is_strict(change):
    ctx = deepcopy(CASES[0]["context"])
    a = ctx["normalized_content"]["assets"][0]
    if change == "foreign":
        a["asset_id"] = "foreign"
    elif change == "url":
        a["url"] = "https://example.com/foreign.svg"
    else:
        ctx["normalized_content"]["assets"].append(deepcopy(a))
    with pytest.raises(ContentPlanError):
        plan(CASES[0], ctx)
