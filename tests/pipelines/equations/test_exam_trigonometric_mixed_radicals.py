"""Keep zero factors, original signs and strict inverse-log radical domains."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import mpmath as mp
import pytest
import sympy as sp

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S, T, U
from solution_runner.pipelines.equations.exam_trigonometric_inverse import decode
from solution_runner.pipelines.equations.exam_trigonometric_log_radical import (
    compile_inverse,
    inverse_power,
)
from solution_runner.pipelines.equations.exam_trigonometric_proof import render
from solution_runner.pipelines.equations.exam_trigonometric_radical_equation import (
    compile_radical,
)
from solution_runner.pipelines.equations.exam_trigonometric_safe_square_proof import (
    checked_values,
    nominal,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_mixed_radicals.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
EXPECTED = DATA["expected"]


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c, formula=None):
    _, f, interval, bounds = read(c["context"])
    return analyze(formula or f, interval, bounds, parent(c))


def plan(c, context=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(context or c["context"], parent_solution_html=parent(c))
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_local_replay_preserves_original_conditions_and_circles(
    c,
):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 987654</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    for t in p.transformations:
        assert not t["transformation_target_id"].startswith("asset:")
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
    )
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert c["context"] == before
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
            before
        )
        == ()
    )


def case(task):
    return next(c for c in CASES if c["task"] == task)


def original_value(task, q):
    x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
    s, c = mp.sin(x), mp.cos(x)
    rad = -mp.cos(2 * x) if task == "686782" else s * c
    if abs(rad) < mp.mpf("1e-55"):
        rad = mp.mpf(0)
    if rad < 0:
        return None
    if task == "629305":
        if q % 1 == R(1, 2) or c <= 0:
            return None
        right = mp.power(1945, mp.log(c) / mp.log(1945))
    else:
        right = c + s if task == "686782" else c
    return mp.sqrt(rad) - right


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_follow_the_original_equation_and_original_log_domain(
    c,
):
    a = analysis(c)
    full = tuple(map(R, EXPECTED[c["task"]]["full"]))
    assert select(a.series, (0, 2, True, False))[0] == full
    assert a.selected == tuple(map(R, EXPECTED[c["task"]]["selected"]))
    assert a.radical_equation.mixed_factors
    with mp.workdps(65):
        for n in range(-216, 217):
            q = R(n, 48)
            v = original_value(c["task"], q)
            assert (v is not None and abs(v) < mp.mpf("1e-45")) == (q % 2 in full)
    if c["task"] == "629305":
        assert a.poles == () and a.radical_equation.positive_arguments == (C,)
        assert a.radical_equation.inverse_identity == (1945, C)
    else:
        assert (
            a.radical_equation.positive_arguments == ()
            and a.radical_equation.inverse_identity is None
        )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_native_source_bytes_root_points_crosses_and_multiple_turn_labels(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    nodes = list(ET.fromstring(raw).iter())
    paths = {n.get("d") for n in nodes if n.tag.endswith("path")}
    a = analysis(c)
    validate(e, a)
    assert {decode(p["angle"]) for p in e["green_markers"]} == set(
        map(R, EXPECTED[c["task"]]["full"])
    )
    for p in e["green_markers"] + e["excluded_markers"]:
        f = p["native_frame"]
        assert p["path_d"] in paths and f["path_d"] in paths
        theta = float(decode(p["angle"]) * sp.pi)
        assert (
            math.hypot(
                p["x"] - f["cx"] - f["rx"] * math.cos(theta),
                p["y"] - f["cy"] + f["ry"] * math.sin(theta),
            )
            < 1
        )
        assert checked_values(a, decode(p["angle"]))[-1] == (p in e["green_markers"])
        for cross in p.get("cross_segments", []):
            assert any(
                n.tag.endswith(cross["tag"]) and dict(n.attrib) == cross["attributes"]
                for n in nodes
            )
            assert (
                math.hypot(cross["center"][0] - p["x"], cross["center"][1] - p["y"]) < 2
            )
    if c["task"] == "530236":
        assert len(e["green_markers"]) == 3 and len(e["labels"]) == 4
        assert e["excluded_markers"][0]["angle"] == "5/4"
        assert len(e["excluded_markers"][0]["cross_segments"]) == 2
    else:
        assert e["excluded_markers"] == []


def test_plain_root_retains_both_zero_cosine_classes_but_log_identity_excludes_both():
    plain = analysis(case("530236"))
    logged = analysis(case("629305"))
    assert plain.branches[0].variable == C and plain.branches[0].residues == (
        R(1, 2),
        R(3, 2),
    )
    assert logged.branches[0].variable == C and logged.branches[0].residues == ()
    for q in (R(1, 2), R(3, 2)):
        assert checked_values(plain, q)[-1]
        assert not checked_values(logged, q)[-1]


def test_parent_cotangent_branch_keeps_zero_cosine_separate_and_checks_the_right_side_sign():
    c = case("686782")
    a = analysis(c)
    html = plan(c).solution_html
    assert a.branches[0].variable == C and a.branches[0].residues == (R(1, 2),)
    assert a.branches[1].variable == U and a.branches[1].values == (-1,)
    assert r"\ctg" in html and r"\tg" not in html
    assert "только в этой ветви разделим на синус" in html
    assert not checked_values(a, R(3, 2))[-1]
    assert "Серию исключаем по исходным ограничениям" in html


def test_inverse_power_proof_explains_original_positive_argument_without_inventing_a_denominator():
    html = plan(case("629305")).solution_html
    assert "положительном аргументе" in html and "взаимную обратность" in html
    assert r"\log_{1945}" in html and r"\text{аргумент логарифма}=0\le0" in html
    assert "знаменатель" not in html
    assert html.index("положительном аргументе") < html.index(
        "возведение в квадрат равносильно"
    )


@pytest.mark.parametrize("base", ["2", "1945", r"\frac{1}{2}"])
@pytest.mark.parametrize("function,argument", [(r"\cos", C), (r"\sin", S)])
def test_inverse_power_reads_the_whole_expression_for_increasing_and_decreasing_bases(
    base, function, argument
):
    formula = (
        r"\sqrt{\sin x\cos x}=(" + base + r")^{\log_{" + base + "}(" + function + " x)}"
    )
    normalized, actual, original_argument = inverse_power(formula)
    assert (
        actual == (R(1, 2) if "frac" in base else R(base))
        and original_argument == argument
    )
    a = analysis(case("629305"), formula)
    assert a.radical_equation.positive_arguments == (argument,)
    assert select(a.series, (0, 2, True, False))[0] == (R(1, 4),)
    assert r"\log_" in render(a, "")[2] and "\\sqrt{" in normalized


@pytest.mark.parametrize(
    "right",
    [
        r"2^{\log_{3}(\cos x)}",
        r"1^{\log_{1}(\cos x)}",
        r"(-2)^{\log_{-2}(\cos x)}",
        r"2^{\log_{2}(-\cos x)}",
        r"2^{\log_{2}(\cos^2 x)}",
        r"2^{\log_{2}(\cos x)+\log_{2}(\sin x)}",
        r"2^{\log_{2}(\cos x)}+1",
        r"\frac{2^{\log_{2}(\cos x)}}{\sin x}\sin x",
        r"2^{\log_{2}(\frac{\cos x}{\sin x})}",
        r"1000001^{\log_{1000001}(\cos x)}",
        r"2^{(\log_{2}(\cos x))^2}",
    ],
)
def test_inverse_power_rejects_mismatched_bases_extra_terms_nested_logs_and_original_poles(
    right,
):
    with pytest.raises(UnsupportedCondition):
        compile_inverse(r"\sqrt{\sin x\cos x}=" + right, parent(case("629305")))


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{\sin x\cos x}=\cos^2 x",
        r"\sqrt{2\cos x-2\cos^3 x}=-2\sin 2x",
        r"\sqrt{\sin x\cos x}+\sqrt{\sin x+\cos x}=\cos x",
        r"\sqrt{\sin x\cos x}=\cos x+\sin x+2",
    ],
)
def test_safe_square_rejects_unreviewed_degrees_and_factorizations(formula):
    with pytest.raises(UnsupportedCondition):
        compile_radical(formula, "safe_square")


def test_original_cancelled_cosine_denominator_is_not_lost():
    a = analysis(case("530236"), r"\frac{\sqrt{\sin x\cos x}\cos x}{\cos x}=\cos x")
    assert a.poles == (C,) and a.radical_equation.positive_arguments == ()
    assert select(a.series, (0, 2, True, False))[0] == (R(1, 4),)
    assert not checked_values(a, R(1, 2))[-1]


@pytest.mark.parametrize(
    "task,formula,variable,value,full",
    [
        (
            "530236",
            r"\sqrt{\sin x\cos x}=\sqrt{3}\cos x",
            T,
            3,
            (sp.atan(3) / sp.pi, R(1, 2), R(3, 2)),
        ),
        (
            "686782",
            r"\sqrt{\sin x\cos x}=\sqrt{3}\sin x",
            U,
            3,
            (sp.S.Zero, sp.atan(R(1, 3)) / sp.pi, sp.S.One),
        ),
    ],
)
def test_tangent_and_cotangent_levels_are_not_restricted_to_the_unit_sine_range(
    task, formula, variable, value, full
):
    a = analysis(case(task), formula)
    assert select(a.series, (0, 2, True, False))[0] == full
    assert any(b.variable == variable and b.candidates == (value,) for b in a.branches)
    html = render(a, "")[2]
    assert "Значение вне отрезка" not in html
    assert html.count("Серия удовлетворяет исходному уравнению") >= 3


@pytest.mark.parametrize(
    "variable,value,offset",
    [(T, 0, 0), (U, 0, R(1, 2)), (U, -1, -R(1, 4)), (T, 3, sp.atan(3) / sp.pi)],
)
def test_nominal_ratio_families_use_the_correct_function(variable, value, offset):
    assert nominal(variable, sp.sympify(value)) == ((offset, 1),)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_circle_or_changed_interval_cannot_reuse_native_asset(c):
    ctx = deepcopy(c["context"])
    asset = ctx["normalized_content"]["assets"][0]
    asset["asset_id"] = "unknown-circle"
    asset["url"] = "/assets/unknown-circle"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    entry = deepcopy(
        CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    )
    entry["bounds"][0] = "-20"
    with pytest.raises(UnsupportedCondition):
        validate(entry, analysis(c))


def test_closed_both_ends_of_a_full_turn_keep_both_source_endpoint_roots():
    a = analysis(case("530236"))
    assert a.selected == (R(1, 2), R(3, 2), R(9, 4), R(5, 2))
    assert select(a.series, (R(1, 2), R(5, 2), False, False))[0] == (R(3, 2), R(9, 4))
