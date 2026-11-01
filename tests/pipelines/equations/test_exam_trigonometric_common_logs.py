"""Common fixed logs retain cancelled poles, zero branches and original argument signs."""

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
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_log_common import (
    PolynomialParser,
    exact_power,
    numeric_bases,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_parser import Parser
from solution_runner.pipelines.equations.exam_trigonometric_log_polynomial import (
    L,
    compile_polynomial,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
    conditions,
    failed,
)
from solution_runner.pipelines.equations.exam_trigonometric_proof import first, formula
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_common_logs.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
EXPECTED = {
    "638312": ((R(3, 4),), (R(11, 4), R(19, 4))),
    "700707": ((R(1, 2),), (R(1, 2),)),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, context=None, prototype=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent(c) if prototype is None else prototype,
        )
    )


def forms(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def original_zero(key, q):
    with mp.workdps(65):
        x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
        s, c = mp.sin(x), mp.cos(x)
        eps = mp.mpf("1e-48")
        if s <= eps:
            return False
        if key == "638312":
            denominator = mp.cos(mp.pi / 2 - x) + mp.cos(3 * mp.pi - x)
            if abs(denominator) < eps:
                return False
            value = (
                (
                    1
                    - mp.log(s) / mp.log(mp.mpf(".5"))
                    - 2 * (mp.log(s) / mp.log(2)) ** 2
                )
                * (s - c)
                / denominator
            )
        else:
            value = (
                (mp.log(s) / mp.log(2)) ** 2
                + mp.log(s * s) / mp.log(2)
                - mp.log(5) / mp.log(2) * mp.log(s) / mp.log(2)
            )
        return abs(value) < mp.mpf("1e-43")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_full_and_selected_roots_satisfy_original_unreduced_logs(c):
    a = analysis(c)
    full, selected = EXPECTED[c["task"]]
    assert (
        a.scale == 1
        and a.selected == selected
        and select(a.series, (0, 2, True, False))[0] == full
    )
    for q in (*full, *selected):
        assert original_zero(c["task"], q) and failed(a, q) is None
    for q in (R(n, 96) for n in range(192)):
        assert original_zero(c["task"], q) == (q in full)


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_catalogue_registration_reuses_shared_handler(g):
    p = get_group_profile(g["key"])
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], 10, g["order"])
    assert (
        p.content_rule_key == "exam-trigonometric-polynomial-circle"
        and g["task_count"] == 1
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_keeps_original_conditions_and_no_assets(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 999</p>"
    p = plan(c, ctx)
    assert (
        p == plan(c)
        and p.condition_html
        == section(before["normalized_content"], "condition")["html"]
    )
    for t in p.transformations:
        assert t["transformation_target_id"].startswith("section:")
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(c, ctx).transformations == () and c["context"] == before
    assert (
        ctx["normalized_content"]["assets"]
        == before["normalized_content"]["assets"]
        == []
    )
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(ctx)
        == ()
    )
    assert "<img" not in p.solution_html
    assert analysis(c).selection_method == "inequalities"


def test_reciprocal_base_identity_keeps_the_original_cancelled_pole_and_partial_sine_level():
    c = case("638312")
    a = analysis(c)
    d = a.log_polynomial
    assert (
        d.base == 2 and d.polynomial == -2 * L * L + L + 1 and d.levels == (1, -R(1, 2))
    )
    assert a.poles == (S - C,) and d.normalization.relations == (
        (R(1, 2), S, -sp.S.One),
    )
    assert d.normalization.cancelled[0] == S - C
    assert failed(a, R(1, 4)) == (S - C, "nonzero", 0) and failed(a, R(3, 4)) is None
    assert not original_zero("638312", R(1, 4))
    html = plan(c).solution_html
    f = forms(html)
    pole = f.index(formula(S - C) + r"\ne0")
    normalization = next(
        i for i, s in enumerate(f) if s.startswith(r"\log_{\frac{1}{2}}")
    )
    assert pole < normalization and "сократим на него" in html
    assert not any(s == formula(S - C) + "=0" for s in f[:normalization])
    assert not any(s.startswith("t=") for s in f)


def test_constant_log_coefficient_preserves_zero_case_and_rejects_value_outside_unit_interval():
    c = case("700707")
    a = analysis(c)
    d = a.log_polynomial
    assert d.normalization.original_arguments == (S, S * S)
    assert d.normalization.relations == ((sp.Integer(2), S * S, sp.Integer(2)),)
    assert sp.expand(d.polynomial - (L * L + (2 - sp.log(5) / sp.log(2)) * L)) == 0
    assert d.levels == (0, -2 + sp.log(5) / sp.log(2)) and d.factor_before
    assert tuple(exact_power(d.base, l) for l in d.levels) == (1, R(5, 4))
    assert conditions(a) == ((S, "positive"), (S * S, "positive"))
    html = plan(c).solution_html
    f = forms(html)
    zero = next(i for i, s in enumerate(f) if s == r"\log_{2}\left(\sin x\right)=0")
    other = next(
        i
        for i, s in enumerate(f)
        if s == r"\log_{2}\left(\sin x\right)=\log_{2}\left(5\right) - 2"
    )
    assert zero < other and "не входит в отрезок от −1 до 1" in html
    assert not any(r"\log{" in s or "constant_log_" in s or "L0" in s for s in f)
    assert not any(s.startswith("t=") for s in f)
    assert (
        "\\log_{2} 5" in f[0]
        and "\\log_2 5"
        in section(c["context"]["normalized_content"], "condition")["html"]
    )


def test_even_positive_argument_powers_do_not_invent_positive_sine_domain():
    c = case("638312")
    _, _, i, b = read(c["context"])
    a = analyze(r"\log_2^{2}(\sin^2x)+\log_4(\sin^4x)=0", i, b, parent(c))
    full = (R(1, 4), R(1, 2), R(3, 4), R(5, 4), R(3, 2), R(7, 4))
    assert select(a.series, (0, 2, True, False))[0] == full
    assert conditions(a) == ((S * S, "positive"), (S**4, "positive"))
    assert failed(a, R(5, 4)) is None
    first(a)


@pytest.mark.parametrize(
    "key,original,replacement,expected",
    [
        ("638312", r"\log_{0,5}", r"\log_{\frac{1}{2}}", EXPECTED["638312"][0]),
        ("700707", r"\log_2 5", r"\log_{2} 4", EXPECTED["700707"][0]),
        ("700707", r"\log_2 5", r"\log_{2} 2", (R(1, 6), R(1, 2), R(5, 6))),
    ],
)
def test_actual_constant_coefficients_and_base_spellings_drive_roots(
    key, original, replacement, expected
):
    c = case(key)
    _, f, i, b = read(c["context"])
    changed = f.replace(original, replacement)
    assert changed != f
    a = analyze(changed, i, b, parent(c))
    assert select(a.series, (0, 2, True, False))[0] == expected
    first(a)


@pytest.mark.parametrize("text", [r"\log_2 5", r"\log_2(5)", r"\log_{2}(5)"])
def test_constant_log_parser_is_bounded_and_old_public_parser_stays_strict(text):
    logs = []
    constants = []
    node = PolynomialParser(text, {}, [], logs, constants=constants).parse()
    assert node.value == sp.log(5) / sp.log(2) and logs == [] and len(constants) == 1
    with pytest.raises(UnsupportedCondition):
        Parser(numeric_bases(text), {}, [], []).parse()


@pytest.mark.parametrize(
    "text",
    [
        r"\log_2(\log_2 4)",
        r"\log_2 0",
        r"\log_2(-1)",
        r"\log_1 5",
        r"\log_{-2}5",
        r"\log_2 1001",
        r"\log_2 5+\log_2 7+\log_2 3",
    ],
)
def test_new_constant_log_parser_rejects_nested_undefined_or_oversized_inputs(text):
    with pytest.raises(UnsupportedCondition):
        PolynomialParser(text, {}, [], []).parse()


def test_numeric_log_spelling_does_not_relax_scalar_digit_spacing():
    assert numeric_bases(r"\log_2 5") == r"\log_{2} 5"
    with pytest.raises(UnsupportedCondition):
        ScalarParser("2 5").parse()
    with pytest.raises(UnsupportedCondition):
        PolynomialParser(r"\log_2 5 6", {}, [], []).parse()


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_2^2(\sin x)+\log_3(\sin x)=0",
        r"\log_2^2(\sin x)+\log_2(\sin^3x)=0",
        r"\log_2^2(\sin x)+\log_2(\cos x)=0",
        r"\frac{\log_2^2(\sin x)}{\log_2(\sin x)}=0",
        r"\log_2^2(\sin x)+\log_2(\sin x)=\log_3 5\log_2(\sin x)",
        r"\log_2^3(\sin x)+\log_2(\sin x)=0",
    ],
)
def test_unreviewed_base_ratios_argument_powers_and_log_denominators_stay_closed(
    formula,
):
    c = case("638312")
    _, _, i, b = read(c["context"])
    with pytest.raises(UnsupportedCondition):
        analyze(formula, i, b, parent(c))


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_extra_method_cannot_be_dropped(c):
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype=parent(c) + "<p>Другое решение</p>")


def test_parenthesized_log_square_keeps_the_same_original_equation():
    c = case("700707")
    _, f, i, b = read(c["context"])
    changed = f.replace(r"\log_2^{2} \sin x", r"\left(\log_2 \sin x\right)^2")
    assert changed != f
    a = analyze(changed, i, b, parent(c))
    assert a.selected == EXPECTED["700707"][1]
    assert select(a.series, (0, 2, True, False))[0] == EXPECTED["700707"][0]
    first(a)


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{(\tg x+\sqrt{3})\log_{13}(2\sin^2x)}{\log_{31}(\sqrt{2}\cos x)}=0",
        r"\log_2^2(\sin x)+\log_3(\cos x)=0",
        r"\sin x\cdot(\log_2^2(\sin x)+\log_4(\sin^2x))=0",
    ],
)
def test_other_log_families_are_released_before_common_base_parent_review(formula):
    assert compile_polynomial(formula, "") is None
