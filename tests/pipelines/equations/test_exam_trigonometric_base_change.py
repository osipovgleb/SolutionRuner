"""Reciprocal base change retains the original pole, linear substitution and SVG."""

import gzip
import hashlib
import json
import math
import re
from copy import deepcopy
from itertools import pairwise
from pathlib import Path
from xml.etree import ElementTree as ET

import mpmath as mp
import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_log_identity import Z
from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
    conditions,
    failed,
)
from solution_runner.pipelines.equations.exam_trigonometric_proof import first
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_base_change.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
ASSET = "0e1261c6-01ce-4cb3-b10b-5798ff5933f3"
SHA = "2f7aa48e220aca268ed0343c13f6fe2a9719067cdb16db03e69dbf6c2e18f5a4"
FULL = (R(1, 3), R(2, 3), R(4, 3), R(5, 3))
SELECTED = (-R(1, 3), R(1, 3), R(2, 3))


def parent(c):
    return section(c["context"]["normalized_content"], "solution")["html"]


def analysis(c, formula=None, prototype=None):
    _, f, i, b = read(c["context"])
    return analyze(formula or f, i, b, prototype or parent(c))


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


def original_zero(q):
    with mp.workdps(65):
        x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
        c = mp.cos(x)
        base, argument = 3 - 4 * c * c, 9 - 16 * c**4
        eps = mp.mpf("1e-48")
        if base <= eps or abs(base - 1) < eps or argument <= eps:
            return False
        denominator = mp.log(base) / mp.log(2)
        if abs(denominator) < eps:
            return False
        return abs(mp.log(argument) / mp.log(base) - 2 - 1 / denominator) < mp.mpf(
            "1e-43"
        )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_match_original_logarithms_and_all_domains(c):
    a = analysis(c)
    assert a.series == ((R(1, 3), 1), (R(2, 3), 1)) and a.selected == SELECTED
    assert select(a.series, (0, 2, True, False))[0] == FULL
    for q in (*FULL, *SELECTED):
        assert original_zero(q) and failed(a, q) is None
    for n in range(192):
        q = R(n, 96)
        assert original_zero(q) == (q in FULL)


def test_original_reciprocal_denominator_is_mapped_to_base_not_one_before_cancellation():
    a = analysis(CASES[0])
    d = a.log_product.equality.identity
    assert a.poles == (2 - 4 * C * C,)
    assert d.kind == "base_square" and d.level == 2 and d.log_value == 1
    assert d.polynomial == 3 * Z - 3 and d.converted == 4 * C * C
    assert (
        d.base_change.offset == 3
        and d.base_change.weight == 4
        and d.base_change.target == 1
    )
    assert (3 - 4 * C * C, "positive") in conditions(a)
    assert (2 - 4 * C * C, "nonzero") in conditions(a)
    assert (9 - 16 * C**4, "positive") in conditions(a)
    assert failed(a, R(1, 4)) == (2 - 4 * C * C, "nonzero", 0)
    assert not original_zero(R(1, 4)) and not original_zero(R(1, 6))


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_catalogue_registration_reuses_existing_handler(g):
    p = get_group_profile(g["key"])
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], 10, 9)
    assert (
        p.content_rule_key == "exam-trigonometric-polynomial-circle"
        and g["task_count"] == 1
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_local_replay_keeps_original_condition_and_asset(
    c,
):
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
    for change in p.transformations:
        assert change["transformation_target_id"].startswith("section:")
        next(
            s
            for s in ctx["normalized_content"]["sections"]
            if s["transformation_target_id"] == change["transformation_target_id"]
        ).update(change["value"])
    assert plan(c, ctx).transformations == () and c["context"] == before
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    assert (
        get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(ctx)
        == ()
    )


def test_original_substitution_product_split_linear_equation_and_circle_order_are_preserved():
    html = plan(CASES[0]).solution_html
    f = forms(html)
    substitution = f.index(r"4 (\cos x)^{2}=t")
    reciprocal = next(i for i, s in enumerate(f) if s.startswith(r"\frac{1}{\log_{2}"))
    product = next(i for i, s in enumerate(f) if s.startswith(r"9 - t^{2}="))
    linear = f.index("3 t - 3=0")
    back = f.index(r"(\cos x)=\pm \frac{1}{2}")
    full = f.index(r"x=\pm\frac{\pi}{3}+\pi k,\quad k\in\mathbb Z")
    assert substitution < reciprocal < product < linear < back < full
    assert not any(s.startswith(r"\log_") and s.endswith("=t") for s in f)
    soup = BeautifulSoup(html, "html.parser")
    first_part, second_part = soup.find_all("li", recursive=True)
    image = first_part.find("img")
    assert image and image["data-asset-id"] == ASSET and second_part.find("img") is None
    assert str(first_part).index("x=\\pm") < str(first_part).index("<img")
    assert not any(s == r"3 - 4 (\cos x)^{2}=0" for s in f)


def test_native_original_svg_has_all_four_valid_markers_and_selected_half_circle():
    raw = gzip.decompress((DIRECTORY / (ASSET + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == SHA == CIRCLES[ASSET]["sha256"]
    root = ET.fromstring(raw)
    paths = [e for e in root.iter() if e.tag.endswith("path")]
    e = CIRCLES[ASSET]
    assert e["residues"] == ["1/3", "2/3", "4/3", "5/3"]
    assert e["bounds"] == ["-1/3", "2/3", True, True] and e["labels"] == [
        "-1/3",
        "1/3",
        "2/3",
    ]
    cx, cy, radius = 73.494, 61.095, 46.941
    for point in e["green_markers"]:
        assert any(
            p.get("d") == point["path_d"] and p.get("fill") == "#067B38" for p in paths
        )
        angle = float(R(point["angle"])) * math.pi
        assert (
            math.hypot(
                point["x"] - cx - radius * math.cos(angle),
                point["y"] - cy + radius * math.sin(angle),
            )
            < 1
        )
    arc = next(
        p for p in paths if p.get("stroke") == "#00487E" and p.get("fill") == "none"
    )
    assert arc.get("stroke-width") == "1.5"
    numbers = list(map(float, re.findall(r"-?\d+(?:\.\d+)?", arc.get("d"))))
    assert len(numbers) == 14
    start = complex(*numbers[:2])
    angles = []
    for offset in (2, 8):
        values = numbers[offset : offset + 6]
        a, b, c = (start + complex(*values[i : i + 2]) for i in (0, 2, 4))
        for n in range(101):
            t = n / 100
            z = (
                (1 - t) ** 3 * start
                + 3 * (1 - t) ** 2 * t * a
                + 3 * (1 - t) * t * t * b
                + t**3 * c
            )
            q = math.atan2(cy - z.imag, z.real - cx) / math.pi
            assert -1 / 3 - 0.01 <= q <= 2 / 3 + 0.01
            assert abs(abs(z - complex(cx, cy)) - radius) < 1
            angles.append(q)
        start = c
    assert abs(angles[0] - 2 / 3) < 0.01 and abs(angles[-1] + 1 / 3) < 0.01
    assert all(b <= a + 0.00001 for a, b in pairwise(angles))


def test_same_certificate_handles_sine_square_without_reusing_the_cosine_source_figure():
    c = CASES[0]
    _, f, _, _ = read(c["context"])
    a = analysis(c, f.replace(r"\cos", r"\sin"))
    assert a.log_product.equality.identity.base_change.variable == S
    assert select(a.series, (0, 2, True, False))[0] == (
        R(1, 6),
        R(5, 6),
        R(7, 6),
        R(11, 6),
    )
    assert a.selected == (-R(1, 6), R(1, 6))
    first(a)


def test_child_coefficient_changes_the_substitution_instead_of_using_the_parent_number():
    a = analysis(
        CASES[0], r"\log_{(6-8\cos^2x)}(36-64\cos^4x)=2+\frac{1}{\log_2(6-8\cos^2x)}"
    )
    d = a.log_product.equality.identity
    assert (
        d.base_change.weight == 8
        and d.base_change.offset == 6
        and d.base_change.target == 2
    )
    assert a.selected == SELECTED and select(a.series, (0, 2, True, False))[0] == FULL
    f = forms(first(a)[1])
    assert r"8 (\cos x)^{2}=t" in f and r"4 (\cos x)^{2}=t" not in f
    for q in FULL:
        assert failed(a, q) is None
        c = sp.cos(q * sp.pi)
        base = 6 - 8 * c * c
        argument = 36 - 64 * c**4
        assert base == 4 and argument == 32
        assert sp.simplify(sp.log(argument, base) - 2 - 1 / sp.log(base, 2)) == 0


def test_changed_constants_retain_forbidden_base_one_even_if_reduced_quadratic_has_roots():
    from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
        branches,
    )
    from solution_runner.pipelines.equations.exam_trigonometric_log_variable import (
        compile_variable,
    )

    a = compile_variable(
        r"\log_{(2-4\cos^2x)}(4-16\cos^4x)=2+\frac{1}{\log_3(2-4\cos^2x)}",
        parent(CASES[0]),
    )
    assert a.log_product.equality.identity.base_change.target == 1
    assert all(b.residues == () for b in branches(a, C))
    for q in FULL:
        assert failed(a, q) == (1 - 4 * C * C, "nonzero", 0)


@pytest.mark.parametrize(
    "old,new",
    [
        (r"[-\frac{\pi}{3};\frac{2\pi}{3}]", r"[\pi;2\pi]"),
        (r"9-16\cos^{4} x", r"9-4\cos^{4} x"),
    ],
)
def test_altered_condition_cannot_reuse_original_circle(old, new):
    c = CASES[0]
    context = deepcopy(c["context"])
    condition = section(context["normalized_content"], "condition")
    assert old in condition["html"]
    condition["html"] = condition["html"].replace(old, new)
    with pytest.raises(UnsupportedCondition):
        plan(c, context)


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_{(3-4\cos^2x)}(9-16\cos^4x)=1+\frac{1}{\log_2(3-4\cos^2x)}",
        r"\log_{(3-4\cos^2x)}(9-16\cos^4x)=2+\frac{1}{\log_2(2-4\cos^2x)}",
        r"\log_{(3-4\cos^2x)}(9-16\cos^4x)=2+\frac{2}{\log_2(3-4\cos^2x)}",
        r"\frac{\log_{(3-4\cos^2x)}(9-16\cos^4x)}{\cos x}=2+\frac{1}{\log_2(3-4\cos^2x)}",
        r"\log_{(3-4\cos^2(2x))}(9-16\cos^4(2x))=2+\frac{1}{\log_2(3-4\cos^2(2x))}",
    ],
)
def test_incompatible_reciprocal_equations_extra_poles_and_angles_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analysis(CASES[0], formula)


def test_unknown_extra_parent_method_is_not_silently_dropped():
    with pytest.raises(UnsupportedCondition):
        plan(CASES[0], prototype=parent(CASES[0]) + "<p>Другое решение</p>")
