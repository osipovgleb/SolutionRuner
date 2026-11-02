"""Cancelled positive powers never cancel the original trigonometric domain."""

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
from solution_runner.pipelines.equations.exam_trigonometric import analyze
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_linear_phase import (
    branch as phase_branch,
)
from solution_runner.pipelines.equations.exam_trigonometric_power_equality import (
    compile_equality,
)
from solution_runner.pipelines.equations.exam_trigonometric_proof import (
    families,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

CASES = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_power_poles.json"
    ).read_text()
)["cases"]
R = sp.Rational
A = sp.acos(sp.sqrt(2) / 4) / sp.pi


def parent(c):
    return section(
        next(x for x in CASES if x["task"] == c["group"])["context"][
            "normalized_content"
        ],
        "solution",
    )["html"]


def analysis(c, formula=None, html=None):
    _, f, i, b = read(c["context"])
    return analyze(formula or f, i, b, parent(c) if html is None else html)


def plan(c, ctx=None):
    ctx = ctx or c["context"]
    h = get_handler(get_group_profile(c["group"]).content_rule_key)
    generated = tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in h.diagram_specs(ctx)
    )
    return h.plan(
        PlanInput(
            ctx, parent_solution_html=parent(c), generated_solution_assets=generated
        )
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_powers_and_original_poles_independently_verify_every_root(c):
    a = analysis(c)
    expected = {
        "673229": (((-R(1, 4), sp.S.One),), (R(-13, 4), R(-9, 4))),
        "673260": (((R(1, 4), sp.S.One),), (R(-15, 4), R(-11, 4))),
        "674023": (((R(1, 4) - A, R(2)), (R(1, 4) + A, R(2))), (R(1, 4) - A,)),
    }
    assert (a.series, a.selected) == expected[c["task"]]
    assert a.poles == ((S,) if c["group"] == "674023" else (C,))
    with mp.workdps(65):
        for q in [*(R(n, 48) for n in range(-216, 217)), *a.residues]:
            x = mp.mpf(str(sp.N(q, 70))) * mp.pi
            s, t = mp.sin(x), mp.cos(x)
            if abs(s if c["group"] == "674023" else t) < mp.mpf("1e-55"):
                assert q % 2 not in a.residues
                continue
            if c["task"] == "673229":
                left = mp.power(mp.mpf(1) / 27, -s / t) * mp.power(3, mp.sin(2 * x))
                right = mp.power(mp.mpf(1) / 9, t * t) * mp.power(3, 3 * s / t)
            elif c["task"] == "673260":
                left = mp.power(16, s / t) * mp.power(2, mp.sin(2 * x))
                right = mp.power(4, t * t) * mp.power(mp.mpf(1) / 2, -4 * s / t)
            else:
                left = mp.power(mp.mpf(1) / 5, t / s) * mp.power(
                    2, mp.cos(2 * x) - mp.sin(2 * x)
                )
                right = mp.power(mp.mpf(1) / 2, s - 1) * mp.power(5, -t / s)
            actual = abs(left - right) / (1 + abs(left) + abs(right)) < mp.mpf("1e-50")
            assert actual == (q % 2 in a.residues)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_local_replay_empty_and_originals_untouched(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 987654</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        items = ctx["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((v for v in items if v["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert all(
        v in ctx["normalized_content"]["assets"]
        for v in before["normalized_content"]["assets"]
    )
    assert len(ctx["normalized_content"]["assets"]) == len(
        before["normalized_content"]["assets"]
    ) + (c["task"] == "674023")
    assert c["context"] == before


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_domain_precedes_power_cancellation_and_parent_method_is_retained(c):
    a = analysis(c)
    html = plan(c).solution_html
    forms = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    pole = r"(\sin x)\ne0" if c["group"] == "674023" else r"(\cos x)\ne0"
    assert forms.index(pole) < next(i for i, v in enumerate(forms) if ">0" in v)
    assert "нарушает область определения" in html
    if c["group"] == "674023":
        from solution_runner.pipelines.equations.exam_trigonometric_proof import formula

        unit = formula(S * S + C * C) + "=1"
        factored = formula(sp.factor(a.reduced, extension=True)) + "=0"
        assert forms.index(unit) < forms.index(factored) < forms.index(r"(\sin x)=0")
        assert all(left != right for left, right in pairwise(forms))
        assert a.selection_method == "circle"
        assert "общий положительный множитель" in html
        assert (
            len(families(a)) == 1
            and r"\pm" in families(a)[0]
            and r"\arccos" in families(a)[0]
        )
        assert r"\frac{\pi}{4}" in families(a)[0]
        assert "preview-" in html
    else:
        assert a.selection_method == "progressions"
        assert "Длина промежутка" in html and "сократим одинаковые слагаемые" in html
        assert "data-asset-id=" not in html


def test_local_svg_corrects_the_false_root_and_marker_without_changing_the_circle():
    c = CASES[-1]
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    corrected = (DIRECTORY / entry["corrected_file"]).read_bytes()
    assert hashlib.sha256(corrected).hexdigest() == entry["corrected_sha256"]
    old = ET.fromstring(raw)
    new = ET.fromstring(corrected)
    assert old.attrib == new.attrib
    changes = entry["correction"]
    old_nodes = [dict(n.attrib) for n in old.iter()]
    new_nodes = [dict(n.attrib) for n in new.iter()]
    expected = []
    for node in old_nodes:
        if node in changes["removed_nonroot_paths"]:
            continue
        copy = dict(node)
        if node == changes["boundary_label_before"]:
            copy = changes["boundary_label_after"]
        for shift in changes["paths"]:
            if node.get("d") == shift["old"]:
                copy["d"] = shift["new"]
        expected.append(copy)
    assert expected == new_nodes
    assert changes["boundary_label_before"]["fill"] == "#007F00"
    assert changes["boundary_label_after"]["fill"] == "#0000FF"
    assert len(changes["removed_nonroot_paths"]) == 2
    assert sum(n.get("fill") == "#007A37" for n in new.iter()) == 1
    frame = changes["native_frame"]
    angle = float(R(1, 4) - A) * math.pi
    target = (
        frame["cx"] + frame["rx"] * math.cos(angle),
        frame["cy"] - frame["ry"] * math.sin(angle),
    )
    for shift in changes["paths"]:
        numbers = list(
            map(
                float,
                re.findall(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", shift["new"]),
            )
        )
        xs, ys = numbers[::2], numbers[1::2]
        assert ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2) == pytest.approx(
            target, abs=1e-8
        )
    bad = entry["green_markers"][0]
    assert math.hypot(bad["x"] - target[0], bad["y"] - target[1]) > 10
    assert entry["point_scope"] == "selected"
    validate(entry, analysis(c))


@pytest.mark.parametrize(
    "denominator,pole", [(r"\cos x", C), (r"2\cos x", C), (r"\sin x", S)]
)
def test_cancelled_exponent_fractions_keep_their_original_pole(denominator, pole):
    formula = rf"3^{{\frac{{{denominator}}}{{{denominator}}}+\sin x}}=3^{{\frac{{{denominator}}}{{{denominator}}}}}"
    compiled = compile_equality(formula, parent(CASES[0]))
    assert compiled.poles == (pole,)
    assert compiled.raw == S


def test_original_pole_can_remove_the_last_numerator_root():
    a = analysis(CASES[-1], formula=r"3^{\ctg x+\cos x}=3^{\ctg x-1}")
    assert a.poles == (S,) and a.residues == a.series == a.selected == ()


@pytest.mark.parametrize("allowed", [False, True])
def test_inverse_phase_is_enabled_only_by_the_reviewed_parent_method(allowed):
    b = phase_branch(2 * S + 2 * C - 1, allow_inverse=allowed)
    if allowed:
        assert b.angle_shift == R(1, 4)
        assert b.candidates == (sp.sqrt(2) / 4,)
        assert len(b.residues) == 2
    else:
        assert b is None


def test_parent_without_inverse_method_cannot_enable_nonstandard_phase():
    c = CASES[-1]
    with pytest.raises(UnsupportedCondition):
        analysis(c, html=parent(c).replace(r"\arccos", r"\cos"))


def test_changed_source_circle_and_selection_interval_are_rejected():
    c = CASES[-1]
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    from dataclasses import replace

    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    with pytest.raises(UnsupportedCondition):
        validate(CIRCLES[aid], replace(analysis(c), bounds=(R(-2), R(0), True, True)))


@pytest.mark.parametrize(
    "formula",
    [
        r"2^{\sin x}=3^{\cos x}",
        r"(-2)^{\sin x}=2^{\cos x}",
        r"3^{\frac{1}{\sin 2x}+\cos x}=3^{\frac{1}{\sin 2x}}",
    ],
)
def test_unknown_power_directions_bases_and_original_poles_are_rejected(formula):
    with pytest.raises(UnsupportedCondition):
        compile_equality(formula, parent(CASES[0]))


@pytest.mark.parametrize(
    "extra", ["<p>Ещё одно решение</p>", r'<span data-inline-latex="t=\sin x"></span>']
)
def test_unreviewed_extra_parent_method_is_rejected(extra):
    with pytest.raises(UnsupportedCondition):
        analysis(CASES[0], html=parent(CASES[0]) + extra)


@pytest.mark.parametrize("key,index", [("673229", 36), ("674023", 37)])
def test_catalog_uses_the_existing_handler(key, index):
    p = get_group_profile(key)
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert p.group_order_index == index
    assert p.snapshot_theme_id == "76619b09-5e8b-45b2-baad-ae54e9eaf162"
