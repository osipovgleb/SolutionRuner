"""Absolute positive powers never cancel a trig factor on an unproved domain."""

import json
from copy import deepcopy
from pathlib import Path

import mpmath as mp
import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_input import read
from solution_runner.pipelines.equations.exam_trigonometric import analyze
from solution_runner.pipelines.equations.exam_trigonometric_absolute import (
    R as ABSOLUTE,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_power_equality import (
    common_exponent,
)
from solution_runner.pipelines.equations.exam_trigonometric_power_parser import (
    PositivePowerParser,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

CASES = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_absolute_power_quotient.json"
    ).read_text()
)["cases"]
CASE = CASES[0]
R = sp.Rational


def parent():
    return section(CASE["context"]["normalized_content"], "solution")["html"]


def analysis(formula=None, prototype=None):
    _, f, i, b = read(CASE["context"])
    return analyze(formula or f, i, b, parent() if prototype is None else prototype)


def plan(context=None, prototype=None):
    handler = get_handler(get_group_profile(CASE["group"]).content_rule_key)
    assert handler.diagram_specs(context or CASE["context"]) == ()
    return handler.plan(
        PlanInput(
            context or CASE["context"],
            parent_solution_html=parent() if prototype is None else prototype,
        )
    )


@pytest.mark.parametrize(
    "weight,radical,expected",
    [
        (r"\sqrt{3}", r"\tg x", (R(1, 6), R(7, 6))),
        ("1", r"\tg x", (R(1, 3), R(4, 3))),
        ("0", r"\tg x", ()),
        ("2", r"\tg x", ()),
        (r"\sqrt{3}", r"-\tg x", (R(5, 6), R(11, 6))),
        ("0", r"\sin x", (R(1, 2),)),
    ],
)
def test_actual_nested_power_equations_domains_and_axis_cases(
    weight, radical, expected
):
    formula = (
        r"\frac{(81^{\left|\cos x\right|})^{\sin x}-9^{"
        + weight
        + r"\sin x}}{\sqrt{"
        + radical
        + "}}=0"
    )
    a = analysis(formula)
    assert a.residues == expected
    assert a.power_equality.absolute_level == (
        C,
        S,
        sp.sqrt(3) / 2 if weight == r"\sqrt{3}" else R(weight) / 2,
    )
    assert all(branch.variable == C for branch in a.branches)
    with mp.workdps(65):
        w = mp.sqrt(3) if weight == r"\sqrt{3}" else mp.mpf(weight)
        for q in [*(R(n, 48) for n in range(-216, 217)), *a.residues, *a.selected]:
            x = mp.mpf(str(sp.N(q, 70))) * mp.pi
            s, c = mp.sin(x), mp.cos(x)
            if radical != r"\sin x" and abs(c) < mp.mpf("1e-55"):
                assert q % 2 not in expected
                continue
            rad = (
                s
                if radical == r"\sin x"
                else (-s / c if radical.startswith("-") else s / c)
            )
            if rad < mp.mpf("1e-55"):
                assert q % 2 not in expected
                continue
            value = (mp.power(mp.power(81, abs(c)), s) - mp.power(9, w * s)) / mp.sqrt(
                rad
            )
            assert (abs(value) < mp.mpf("1e-48")) == (q % 2 in expected)


def test_original_selection_and_parent_domain_before_cancel_before_absolute_level():
    a = analysis()
    assert a.selected == (-R(11, 6), -R(5, 6)) and a.series == ((R(1, 6), sp.S.One),)
    html = plan().solution_html
    f = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    domain = f.index(r"\tgx>0")
    canceled = f.index(r"(\sin x)\ne0")
    level = next(i for i, v in enumerate(f) if v.startswith(r"\left|") and "=" in v)
    assert domain < canceled < level
    assert r"(\cos x)^{2}=\frac{3}{4}" in f
    assert "Нули сокращаемого множителя" in html and "<img" not in html
    assert "двойн" in BeautifulSoup(parent(), "html.parser").get_text().replace(
        "\xad", ""
    )


def test_saved_answers_unused_and_replay_preserves_original_sources():
    before = deepcopy(CASE["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 999</p>"
    p = plan(ctx)
    assert (
        p == plan()
        and p.condition_html
        == section(before["normalized_content"], "condition")["html"]
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert key.startswith("section:") and not key.startswith("section:condition")
        next(
            v
            for v in ctx["normalized_content"]["sections"]
            if v["transformation_target_id"] == key
        ).update(t["value"])
    assert plan(ctx).transformations == () and CASE["context"] == before
    assert (
        ctx["normalized_content"]["assets"]
        == before["normalized_content"]["assets"]
        == []
    )


def test_unjustified_cancellation_must_not_lose_the_original_zero_root():
    _, f, _, _ = read(CASE["context"])
    changed = f.replace(r"\sqrt{\tg x}", r"\sqrt{\cos x}")
    # At x=0 the original numerator vanishes and the new denominator equals one.
    assert 81**0 - 9**0 == 0
    with pytest.raises(UnsupportedCondition, match="can vanish"):
        analysis(changed)


@pytest.mark.parametrize(
    "old,new",
    [
        (r"\cos x", r"\cos 2x"),
        (r"\left|\cos x\right|", "r"),
        ("81", "-81"),
        (r"\sqrt{3}\sin x", r"3\sin x"),
        (r"\sqrt{3}\sin x", r"\sqrt{3}\cos x"),
        ("81", "7"),
    ],
)
def test_unknown_parameters_angles_levels_bases_and_exponent_directions_fail_closed(
    old, new
):
    _, f, _, _ = read(CASE["context"])
    changed = f.replace(old, new)
    assert changed != f
    with pytest.raises(UnsupportedCondition):
        analysis(changed)


def test_placeholder_capability_is_limited_to_the_absolute_parser():
    with pytest.raises(UnsupportedCondition):
        PositivePowerParser("3^{r}", {}, []).parse()
    with pytest.raises(UnsupportedCondition):
        common_exponent({3: ABSOLUTE * S}, {})
    base, exponent = common_exponent({3: ABSOLUTE * S}, {}, extra_symbols=(ABSOLUTE,))
    assert base == 3 and exponent == ABSOLUTE * S


def test_parent_method_must_keep_complete_absolute_exponent_algebra():
    changed = parent().replace(r"\left|\cos x\right|", r"\cos x")
    with pytest.raises(UnsupportedCondition):
        plan(prototype=changed)
    with pytest.raises(UnsupportedCondition):
        plan(prototype=parent() + "<p>Другое решение</p>")


def test_exact_catalog_binding_uses_the_shared_handler():
    p = get_group_profile("687074")
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (
        "bdea7c06-2468-453b-a2c4-c6237a7c2071",
        "76619b09-5e8b-45b2-baad-ae54e9eaf162",
        11,
        41,
    )
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
