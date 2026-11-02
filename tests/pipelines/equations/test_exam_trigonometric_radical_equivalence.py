"""Equivalent squaring retains both root domains, cubic roots and native turns."""

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
from solution_runner.pipelines.equations.exam_trigonometric_equal_radicals import (
    compile_equality,
    reviewed_parent,
)
from solution_runner.pipelines.equations.exam_trigonometric_radical_equation import (
    branches,
    compile_radical,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

CASES = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_radical_equivalence.json"
    ).read_text()
)["cases"]
R = sp.Rational
EXPECTED = {
    "549671": ((R(1, 2),), (R(77, 2), R(81, 2))),
    "639950": ((R(2, 3), R(4, 3)), (R(14, 3),)),
    "640519": ((R(1, 3), R(5, 3)), (-R(7, 3),)),
    "656084": ((R(1, 6), R(5, 6)), (-R(11, 6),)),
    "656254": ((R(7, 6), R(11, 6)), (-R(17, 6),)),
}
COEFFICIENTS = {
    "639950": (2, -4, 3, 6, "cos"),
    "640519": (4, 9, 6, 11, "cos"),
    "656084": (2, 10, 2, 7, "sin"),
    "656254": (2, -2, 7, 9, "sin"),
}


def parent(c):
    source = next(v for v in CASES if v["task"] == c["group"])
    return section(source["context"]["normalized_content"], "solution")["html"]


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, context=None, prototype=None):
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    assert handler.diagram_specs(context or c["context"]) == ()
    return handler.plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent(c) if prototype is None else prototype,
        )
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_equations_and_all_selected_roots_are_independently_verified(c):
    a = analysis(c)
    assert (a.residues, a.selected) == EXPECTED[c["task"]]
    d = a.radical_equation
    if c["group"] == "549671":
        assert d.kind == "safe_square" and d.right_radicand is None
        assert a.raw == -(S**3) - 3 * S**2 + 4
        assert set(a.branches[0].candidates) == {1, -2}
    else:
        assert d.kind == "equal_roots" and d.right_radicand is not None
        assert d.right == sp.sqrt(d.right_radicand)
        assert d.conditions == (d.radicand, d.right_radicand)
        assert sp.expand(d.squared - d.radicand + d.right_radicand) == 0
    with mp.workdps(65):
        for q in [*(R(n, 48) for n in range(-216, 217)), *a.residues, *a.selected]:
            x = mp.mpf(str(sp.N(q, 70))) * mp.pi
            s, t = mp.sin(x), mp.cos(x)
            if c["task"] == "549671":
                rad = mp.cos(2 * x) - s**3 + 3
                zero = rad >= 0 and abs(mp.sqrt(max(0, rad)) - s) < mp.mpf("1e-45")
            else:
                A, B, D, F, unit = COEFFICIENTS[c["task"]]
                u = t if unit == "cos" else s
                left, right = A * u * u + B * u + D, u + F
                zero = min(left, right) >= 0 and abs(
                    mp.sqrt(max(0, left)) - mp.sqrt(max(0, right))
                ) < mp.mpf("1e-45")
            assert zero == (q % 2 in a.residues)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_replay_preserves_conditions_and_original_figures(c):
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
        key = t["transformation_target_id"]
        assert key.startswith("section:") and not key.startswith("section:condition")
        next(
            v
            for v in ctx["normalized_content"]["sections"]
            if v["transformation_target_id"] == key
        ).update(t["value"])
    assert plan(c, ctx).transformations == () and c["context"] == before
    assert ctx["normalized_content"]["assets"] == before["normalized_content"]["assets"]
    aid = before["normalized_content"]["assets"][0]["asset_id"]
    assert p.solution_html.count('data-asset-id="' + aid + '"') == 1
    a = analysis(c)
    assert a.image_position == "before-intro"
    validate(CIRCLES[aid], a)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_proof_preserves_root_equivalence_or_cubic_sign_then_rejects_outside_unit_values(
    c,
):
    html = plan(c).solution_html
    forms = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert "вне отрезка от −1 до 1" in html
    if c["group"] == "549671":
        assert any("^{3}" in f for f in forms)
        assert any(r"\ge" in f and r"\sin" in f for f in forms)
        assert any("(2" not in f and ")^{2}" in f and r"\sin" in f for f in forms)
        assert any("77" in f for f in forms) and any("81" in f for f in forms)
    else:
        assert (
            "Квадратные корни равны" in html and "подкоренное выражение справа" in html
        )
        d = analysis(c).radical_equation
        assert d.right_radicand is not None
        outside = next(v for v in analysis(c).branches[0].candidates if abs(v) > 1)
        inside = next(v for v in analysis(c).branches[0].candidates if abs(v) <= 1)
        index = lambda value: next(
            i for i, f in enumerate(forms) if f.endswith("=" + sp.latex(value))
        )
        assert index(outside) < index(inside)


def residues(e, preferred=S):
    return tuple(
        sorted({q for b in branches(e, preferred, True)[1] for q in b.residues})
    )


@pytest.mark.parametrize(
    "formula,expected",
    [
        (r"\sqrt{\cos 2x-\sin^3x+3}=-\sin x", ()),
        (r"\sqrt{\sin^2x-\sin x(\sin x+2)^2}=\sin x", (R(0), R(1))),
        (r"\sqrt{\sin^2x-(\sin x-\frac{1}{2})(\sin x+2)^2}=\sin x", (R(1, 6), R(5, 6))),
        (r"\sqrt{1+\sin^3x}=\cos x", (R(0), R(3, 2))),
    ],
)
def test_bounded_cubic_extension_keeps_zero_roots_and_original_right_sign(
    formula, expected
):
    assert residues(compile_radical(formula, "safe_square")) == expected


@pytest.mark.parametrize(
    "formula,expected",
    [
        (
            r"\sqrt{\cos x+(\cos x-\frac{1}{2})(\cos x+\frac{1}{2})}=\sqrt{\cos x}",
            (R(1, 3), R(5, 3)),
        ),
        (
            r"\sqrt{\cos x+\cos x(\cos x-\frac{1}{2})}=\sqrt{\cos x}",
            (R(1, 3), R(1, 2), R(3, 2), R(5, 3)),
        ),
        (
            r"\sqrt{\cos x-2+(\cos x-\frac{1}{2})(\cos x+\frac{1}{2})}=\sqrt{\cos x-2}",
            (),
        ),
    ],
)
def test_both_radicand_domains_are_checked_and_zero_radicands_remain_allowed(
    formula, expected
):
    assert residues(compile_equality(formula), C) == expected


def test_negative_right_radicand_is_rejected_without_evaluating_a_complex_root():
    from solution_runner.pipelines.equations.exam_trigonometric_proof import first

    c = next(c for c in CASES if c["task"] == "639950")
    _, _, interval, bounds = read(c["context"])
    formula = (
        r"\sqrt{\cos x-2+(\cos x-\frac{1}{2})(\cos x+\frac{1}{2})}=\sqrt{\cos x-2}"
    )
    a = analyze(formula, interval, bounds, parent(c))
    assert a.residues == a.selected == ()
    assert "подкоренное выражение справа" in first(a)[1]


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{\cos x+2}=\sqrt{\cos x+2}",
        r"\sqrt{\cos^2x+1}=\sqrt{\cos x+2}+\sin x",
        r"2\sqrt{\cos^2x+1}=\sqrt{\cos x+2}",
        r"\sqrt{\cos^2x+1}\sqrt{\sin x+2}=\sqrt{\cos x+2}",
        r"\sqrt{\cos^4x+1}=\sqrt{\cos x+2}",
        r"\sqrt{\cos^2x+1}=\sqrt{\tg x+2}",
        r"\sqrt{\cos^2(2x)+1}=\sqrt{\cos 2x+2}",
        r"\sqrt{\cos^2x+r}=\sqrt{\cos x+2}",
    ],
)
def test_identities_root_sums_products_degrees_poles_angles_and_parameters_fail_closed(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        compile_equality(formula)


def test_parent_cannot_drop_the_radicand_domain_or_add_another_method():
    c = next(c for c in CASES if c["task"] == "639950")
    changed = parent(c).replace(r"\ge", r"\le")
    assert changed != parent(c)
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype=changed)
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype=parent(c) + "<p>Другое решение</p>")
    with pytest.raises(UnsupportedCondition):
        plan(
            c,
            prototype=parent(c) + '<p><span data-inline-latex="t=\\cos x"></span></p>',
        )


def test_unrelated_parent_keeps_valid_spacing_between_power_and_angle():
    data = json.loads(
        (
            Path(__file__).parent / "fixtures/category_14_trigonometric_methods.json"
        ).read_text()
    )
    c = next(c for c in data["cases"] if c["task"] == "507583")
    html = section(c["context"]["normalized_content"], "solution")["html"]
    assert r"\cos^2 4x" in html
    assert reviewed_parent(html) is False


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_native_figures_keep_all_source_bytes_frames_turns_and_exact_selection(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[aid]
    svg = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(svg).hexdigest() == entry["sha256"]
    paths = {n.get("d") for n in ET.fromstring(svg).iter() if n.tag.endswith("path")}
    assert entry["native_circle_path"] in paths
    for p in entry["green_markers"]:
        f = p["native_frame"]
        assert p["path_d"] in paths and f["path_d"] in paths
        theta = float(R(p["angle"])) * math.pi
        assert (
            math.hypot(
                p["x"] - f["cx"] - f["rx"] * math.cos(theta),
                p["y"] - f["cy"] + f["ry"] * math.sin(theta),
            )
            < 2
        )
    if c["task"] == "549671":
        frames = [p["native_frame"] for p in entry["green_markers"]]
        assert len(frames) == 2 and all(
            f["rx"] > 80
            and f["path_d"] != entry["native_circle_path"]
            and f["fit_residual"] < 1
            for f in frames
        )
        assert abs(frames[0]["rx"] - frames[1]["rx"]) > 9
        assert entry["bounds"] == ["73/2", "41", False, True]
    if c["task"] in ("639950", "656084"):
        assert entry["point_scope"] == "selected" and len(entry["residues"]) == 1
        assert len(entry["complete_residues"]) == 2
    changed = deepcopy(entry)
    changed["bounds"][0] = "0"
    with pytest.raises(UnsupportedCondition):
        validate(changed, analysis(c))
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)


@pytest.mark.parametrize(
    "key,uuid,index",
    [
        ("549671", "46a84ce1-4a8b-4ff5-aec2-d75ccf8d50ee", 26),
        ("639950", "0aa7c709-d3f0-49be-a36d-748c7eca1af1", 40),
    ],
)
def test_exact_catalog_bindings_reuse_the_existing_trigonometric_handler(
    key, uuid, index
):
    p = get_group_profile(key)
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (uuid, "29795b40-48bf-4ad6-9f1f-5c4f5c301a30", 10, index)
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
