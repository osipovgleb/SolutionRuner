"""Sum identities, triple angles, parent notes, and reviewed quadratic families."""

import gzip
import hashlib
import json
import math
import re
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import (
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
    validate,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    decode,
    ordered,
    turn,
)
from solution_runner.pipelines.equations.exam_trigonometric_prepared_circle import (
    recipe,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_identity_notes.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
SELECTED = {
    "672798": "-5/4 -1/4",
    "672938": "-3/4",
    "676901": "-1/3 1/4",
    "678380": "-5/4 -3/4 -1/3 -1/4",
    "680573": "11/3",
    "680793": "29/6",
    "681151": "-3 -2 -7/4",
    "681163": "-1/6 1/4 3/4",
    "681164": "7/3 8/3 19/6",
    "681218": "-14/3 -13/3 -23/6",
    "681211": "1/4 3/4 4/3",
    "681212": "-1/3 -1/4",
    "685382": "13/4 15/4 13/3",
    "681242": "-7/2 -8/3",
    "681271": "-3/2 -3/4",
    "681243": "-1/2 1/4",
    "681294": "-14/3 -13/3 -7/2",
    "681195": "-11/4 -9/4 -3/2",
    "681293": "3/2 7/3",
    "682554": "-11/6 -3/2 -7/6",
    "682547": "4/3 3/2 5/3",
    "682614": "5/3 2 7/3 3",
    "682680": "3 15/4 4",
    "690243": "-11/24 -13/36 -1/36 1/24 11/36",
}
RESIDUES = {
    "672798": "3/4 7/4",
    "672938": "1/4 5/4",
    "676901": "1/4 2/3 3/4 5/3",
    "678380": "1/4 1/3 3/4 5/4 5/3 7/4",
    "680573": "4/3 5/3",
    "680793": "5/6 7/6",
    "681151": "0 1/4 3/4 1",
    "681163": "1/4 3/4 7/6 11/6",
    "681164": "1/3 2/3 7/6 11/6",
    "681218": "1/6 5/6 4/3 5/3",
    "681211": "1/4 3/4 4/3 5/3",
    "681212": "5/4 4/3 5/3 7/4",
    "685382": "1/3 2/3 5/4 7/4",
    "681242": "1/2 4/3 5/3",
    "681271": "1/2 5/4 7/4",
    "681243": "1/4 3/4 3/2",
    "681294": "1/2 4/3 5/3",
    "681195": "1/2 5/4 7/4",
    "681293": "1/3 2/3 3/2",
    "682554": "1/6 1/2 5/6 7/6 3/2 11/6",
    "682547": "1/3 1/2 2/3 4/3 3/2 5/3",
    "682614": "0 1/3 1 5/3",
    "682680": "0 1/4 1 7/4",
    "690243": "1/24 11/36 13/24 23/36 35/36 25/24 47/36 37/24 59/36 71/36",
}
ORIGINAL = {
    "672798": sp.sin(X + sp.pi / 6) + sp.sin(X + sp.pi / 3) - sp.sin(X + sp.pi / 4),
    "672938": sp.sin(X - sp.pi / 6) + sp.sin(X - sp.pi / 3) - sp.sin(X - sp.pi / 4),
    "676901": 2 * s * s
    + sp.sqrt(2) * sp.sin(2 * sp.pi - X)
    + sp.sqrt(3) * sp.sin(2 * X)
    - sp.sqrt(6) * c,
    "678380": sp.cos(3 * X) - sp.cos(2 * X) + c,
    "680573": 2 * sp.sin(2 * X)
    + sp.sqrt(20) * sp.sin(X + sp.pi)
    - 2 * sp.sqrt(3) * sp.sin(X - sp.pi / 2)
    - sp.sqrt(15),
    "680793": 2 * sp.sin(2 * X)
    + sp.sqrt(20) * sp.cos(X + sp.pi)
    - 2 * sp.sqrt(3) * sp.cos(X - 3 * sp.pi / 2)
    - sp.sqrt(15),
    "681151": 2 * sp.sqrt(2) * sp.sin(X + sp.pi / 3) + 2 * c * c - 2 - sp.sqrt(6) * c,
    "681163": 2 * s + 2 * sp.sqrt(2) * sp.sin(-X) - 4 * c * c - sp.sqrt(2) + 4,
    "681164": 2 * s + 2 * sp.sqrt(3) * sp.sin(-X) - 4 * c * c - sp.sqrt(3) + 4,
    "681218": 2 * sp.sin(-X) + 2 * sp.sqrt(3) * s - 4 * c * c - sp.sqrt(3) + 4,
    "681211": 2 * sp.cos(2 * sp.pi + 2 * X)
    - 2
    + sp.sqrt(8) * s
    + sp.sqrt(6)
    - sp.sqrt(12) * s,
    "681212": 2 * sp.cos(2 * sp.pi + 2 * X)
    - 2
    - sp.sqrt(8) * s
    - sp.sqrt(6)
    - sp.sqrt(12) * s,
    "685382": 2
    + 2 * sp.cos(sp.pi - 2 * X)
    + sp.sqrt(8) * s
    - sp.sqrt(6)
    - sp.sqrt(12) * s,
    "681242": 2 - 2 * c * c + sp.sqrt(3) * s - sp.sqrt(3) + 2 * sp.sin(X + sp.pi),
    "681271": 2 - 2 * c * c + sp.sqrt(2) * s - sp.sqrt(2) + 2 * sp.sin(X - sp.pi),
    "681243": 1 - sp.cos(2 * X) + sp.sqrt(2) * sp.sin(X - sp.pi) - sp.sqrt(2) + 2 * s,
    "681294": 1 - sp.cos(2 * X) + sp.sqrt(3) * s - sp.sqrt(3) + 2 * sp.sin(X - sp.pi),
    "681195": 1 - sp.cos(2 * X) + sp.sqrt(2) * s - sp.sqrt(2) + 2 * sp.sin(X + sp.pi),
    "681293": 1 - sp.cos(2 * X) + sp.sqrt(3) * sp.sin(X + sp.pi) - sp.sqrt(3) + 2 * s,
    "682554": 4 * c**3 + 3 * sp.sin(X - sp.pi / 2),
    "682547": 4 * c**3 + sp.sin(X - sp.pi / 2),
    "682614": 2 * c**3 - 2 * c + s * s,
    "682680": sp.sqrt(2) * c**3 - sp.sqrt(2) * c + s * s,
    "690243": sp.sqrt(3) * c - s - 2 * sp.cos(5 * X),
}
IDENTITY = {
    "672798": (2 * sp.cos(sp.pi / 12) - 1) * sp.sin(X + sp.pi / 4),
    "672938": (2 * sp.cos(sp.pi / 12) - 1) * sp.sin(X - sp.pi / 4),
    "676901": (2 * s - sp.sqrt(2)) * (s + sp.sqrt(3) * c),
    "678380": sp.cos(2 * X) * (2 * c - 1),
    "680573": (2 * c - sp.sqrt(5)) * (2 * s + sp.sqrt(3)),
    "680793": (2 * s - sp.sqrt(5)) * (2 * c + sp.sqrt(3)),
    "681151": s * (sp.sqrt(2) - 2 * s),
    "681163": (2 * s + 1) * (2 * s - sp.sqrt(2)),
    "681164": (2 * s + 1) * (2 * s - sp.sqrt(3)),
    "681218": (2 * s - 1) * (2 * s + sp.sqrt(3)),
    "681211": -(2 * s - sp.sqrt(2)) * (2 * s + sp.sqrt(3)),
    "681212": -(2 * s + sp.sqrt(2)) * (2 * s + sp.sqrt(3)),
    "685382": (2 * s - sp.sqrt(3)) * (2 * s + sp.sqrt(2)),
    "681242": (2 * s + sp.sqrt(3)) * (s - 1),
    "681271": (2 * s + sp.sqrt(2)) * (s - 1),
    "681243": (2 * s - sp.sqrt(2)) * (s + 1),
    "681294": (2 * s + sp.sqrt(3)) * (s - 1),
    "681195": (2 * s + sp.sqrt(2)) * (s - 1),
    "681293": (2 * s - sp.sqrt(3)) * (s + 1),
    "682554": sp.cos(3 * X),
    "682547": c * (4 * c * c - 1),
    "682614": (c * c - 1) * (2 * c - 1),
    "682680": (c * c - 1) * (sp.sqrt(2) * c - 1),
    "690243": 4 * sp.sin(3 * X + sp.pi / 12) * sp.sin(2 * X - sp.pi / 12),
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return next(
        s["html"]
        for p in CASES
        if p["task"] == c["group"]
        for s in p["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, context=None):
    ctx = context or c["context"]
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    generated = tuple(
        {
            **spec,
            "source_asset_id": "preview-" + spec["sha256"][:16],
            "url": "/assets/preview-" + spec["sha256"][:16],
        }
        for spec in handler.diagram_specs(ctx)
    )
    return handler.plan(
        PlanInput(
            ctx, parent_solution_html=parent(c), generated_solution_assets=generated
        )
    )


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_registration_extends_one_shared_rule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
        p.category_key,
    ) == (g["uuid"], g["theme_uuid"], 6, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_algebra_and_complete_and_selected_roots_are_independent(c):
    task = c["task"]
    a = analysis(c)
    difference = sp.expand(sp.expand_trig(ORIGINAL[task] - IDENTITY[task])).xreplace(
        {sp.sin(X): S, sp.cos(X): C}
    )
    assert sp.simplify(sp.rem(difference, S * S + C * C - 1, S)) == 0
    assert a.selected == tuple(map(sp.sympify, SELECTED[task].split()))
    assert select(a.series, (0, 2, True, False))[0] == tuple(
        map(sp.Rational, RESIDUES[task].split())
    )
    for q in a.selected:
        assert (
            sp.simplify(
                (IDENTITY[task] if task == "690243" else ORIGINAL[task]).subs(
                    X, q * sp.pi
                )
            )
            == 0
        )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_replay_preserves_conditions_and_sources(c):
    original = deepcopy(c["context"])
    p = plan(c)
    assert c["context"] == original
    changed = deepcopy(original)
    for s in changed["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>не использовать</p>"
    assert (
        plan(c, changed).answer == p.answer
        and plan(c, changed).solution_html == p.solution_html
    )
    for t in p.transformations:
        key = t["transformation_target_id"]
        assert not key.startswith("section:condition")
        items = changed["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((s for s in items if s["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, changed).transformations == ()
    assert (
        changed["normalized_content"]["assets"][
            : len(original["normalized_content"]["assets"])
        ]
        == original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_figures_match_complete_or_selected_points_and_keep_original_bytes(c):
    a = analysis(c)
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    specs = handler.diagram_specs(c["context"])
    assert bool(specs) == (c["task"] in ("672938", "681163"))
    assets = c["context"]["normalized_content"]["assets"]
    if not assets:
        e = recipe(c["context"])
        if c["task"] in ("680573", "680793"):
            assert e is None and a.selection_method == "inequalities"
            return
        assert c["task"] == "672938" and e is not None
    else:
        asset = assets[0]["asset_id"]
        e = CIRCLES[asset]
        assert (
            hashlib.sha256(
                gzip.decompress((DIRECTORY / (asset + ".svgz")).read_bytes())
            ).hexdigest()
            == e["sha256"]
        )
    validate(e, a)
    expected = (
        ordered(turn(q) for q in a.selected)
        if e.get("point_scope") == "selected"
        else select(a.series, (0, 2, True, False))[0]
    )
    assert tuple(map(decode, e["residues"])) == expected
    assert len(BeautifulSoup(plan(c).solution_html, "html.parser").find_all("img")) == 1


@pytest.mark.parametrize("task", ["672798", "672938"])
def test_mean_angle_sum_keeps_nonzero_constant_and_avoids_translated_quadratic(task):
    a = analysis(case(task))
    assert a.translation == 0 and a.sum_product.kind == "constant_sum"
    assert len(a.branches) == 1
    coefficient = a.sum_product.identities[1][0]
    assert sp.simplify(coefficient - (-1 + sp.sqrt(2) / 2 + sp.sqrt(6) / 2)) == 0
    html = plan(case(task)).solution_html
    assert "формулу суммы синусов" in html and "множитель ненулевой" in html
    assert "квадратному" not in html and "D=" not in html


def test_missing_child_circle_has_only_selected_point_and_full_root_certificate():
    c = case("672938")
    e = recipe(c["context"])
    assert e["complete_residues"] == ["1/4", "5/4"] and e["labels"] == ["-3/4"]
    root = ET.fromstring((DIRECTORY / e["file"]).read_text())
    markers = root.findall('.//*[@data-role="selected-root"]')
    assert len(markers) == 1 and markers[0].get("data-root") == "-3/4"
    point = markers[0]
    assert float(point.get("cx")) == pytest.approx(115 - 72 / math.sqrt(2), abs=1e-7)
    assert float(point.get("cy")) == pytest.approx(120 + 72 / math.sqrt(2), abs=1e-7)
    assert (
        root.find('.//*[@data-role="interval-arc"]').get("d")
        == "M115 48 A72 72 0 1 0 187 120"
    )
    with pytest.raises(UnsupportedCondition):
        validate(e, replace(analysis(c), residues=(sp.Rational(5, 4),)))


def test_source_half_sine_points_and_all_three_projection_segments_are_corrected():
    c = case("681163")
    asset = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[asset]
    root = ET.fromstring((DIRECTORY / e["corrected_file"]).read_text())
    cx, cy, radius = e["circle"]
    corrected = root.findall(".//*[@data-corrected-angle]")
    assert len(corrected) == 4
    for node in corrected:
        angle = node.get("data-corrected-angle")
        q = float(sp.Rational(angle))
        old = next(m for m in e["green_markers"] if m["angle"] == angle)
        dx, dy = map(float, re.findall(r"[-\d.]+", node.get("transform")))
        assert old["inaccurate"]
        assert old["x"] + dx == pytest.approx(
            cx + radius * math.cos(q * math.pi), abs=1e-7
        )
        assert old["y"] + dy == pytest.approx(
            cy - radius * math.sin(q * math.pi), abs=1e-7
        )
    projections = root.findall('.//*[@data-role="corrected-projection"]')
    assert len(projections) == 3
    assert all(
        float(p.get("y1")) == pytest.approx(cy + radius / 2)
        and p.get("y1") == p.get("y2")
        for p in projections
    )


@pytest.mark.parametrize("task", ["682554", "682547"])
def test_triple_angle_and_factorization_note_adapt_to_child_coefficient(task):
    a = analysis(case(task))
    data = a.triple_angle
    assert data.note and data.leading == 1
    assert data.remainder == (0 if task == "682554" else 2)
    if task == "682554":
        assert a.scale == 3 and a.series == ((sp.Rational(1, 6), sp.Rational(1, 3)),)
    else:
        assert a.scale == 1 and a.series[0] == (sp.Rational(1, 2), sp.S.One)
        assert sp.Rational(1, 6) not in select(a.series, (0, 2, True, False))[0]
        assert sp.simplify(ORIGINAL[task].subs(X, sp.pi / 6)) != 0
    html = plan(case(task)).solution_html
    assert html.index("тройного угла") < html.index("Примечание")
    assert html.count("Вынесем общий множитель и решим полученные уравнения") == 1
    assert (
        len(BeautifulSoup(html, "html.parser").find_all("img")) == 1
        and "D=" not in html
    )


@pytest.mark.parametrize("task", ["682614", "682680"])
def test_cubic_boundary_levels_merge_without_losing_common_binomial_grouping(task):
    a = analysis(case(task))
    b = a.branches[0]
    assert b.grouping and a.series[0] == (sp.S.Zero, sp.S.One)
    html = plan(case(task)).solution_html
    assert "Сгруппируем слагаемые" in html
    common = 2 * C - 1 if task == "682614" else sp.sqrt(2) * C - 1
    assert sp.simplify(sp.cancel(a.reduced / common) - (C * C - 1)) == 0


def test_auxiliary_cosine_has_two_shifted_sine_factors_and_both_selection_methods():
    a = analysis(case("690243"))
    assert a.sum_product.kind == "auxiliary_cosine" and a.selection_note
    assert [b.angle_scale for b in a.branches] == [3, 2]
    assert [b.angle_shift for b in a.branches] == [
        sp.Rational(1, 12),
        -sp.Rational(1, 12),
    ]
    assert all(b.variable == S for b in a.branches)
    assert a.series == (
        (-sp.Rational(1, 36), sp.Rational(1, 3)),
        (sp.Rational(1, 24), sp.Rational(1, 2)),
    )
    html = plan(case("690243")).solution_html
    assert (
        html.index("вспомогательный угол")
        < html.index("формулу разности")
        < html.index("Примечание")
        < html.index("целого параметра")
    )
    assert len(BeautifulSoup(html, "html.parser").find_all("img")) == 1


@pytest.mark.parametrize("task", ["680573", "680793"])
def test_impossible_affine_level_is_explicitly_rejected_without_losing_real_branch(
    task,
):
    a = analysis(case(task))
    html = plan(case(task)).solution_html
    assert any(
        sp.sqrt(5) / 2 in b.candidates and sp.sqrt(5) / 2 not in b.values
        for b in a.branches
    )
    assert "не входит в отрезок" in html and not BeautifulSoup(
        html, "html.parser"
    ).find("img")


@pytest.mark.parametrize(
    "formula",
    [
        r"\sin(x+\frac{\pi}{6})+\sin(x+\frac{\pi}{3})=\sin(x+\frac{\pi}{3})",
        r"\sin(x+\frac{\pi}{3})+\sin(x-\frac{\pi}{3})=\sin x",
        r"2\sin x+\sin2x=\sin3x",
        r"\frac{\sin x}{\cos x}+\sin(x+\frac{\pi}{6})=\sin(x+\frac{\pi}{3})",
    ],
)
def test_unreviewed_or_zero_mean_angle_factor_fails_closed(formula):
    from solution_runner.pipelines.equations.exam_trigonometric_sum_identities import (
        compile_identity,
    )

    with pytest.raises(UnsupportedCondition):
        compile_identity(formula, "constant_sum")


@pytest.mark.parametrize(
    "formula",
    [
        r"\sqrt{3}\cos x-\sin x=3\cos5x",
        r"\cos x+\sqrt{5}\sin x=\sqrt{6}\cos5x",
        r"\sqrt{3}\cos x-\sin x+\sin3x=2\cos5x",
        r"\cos x=\cos5x",
    ],
)
def test_auxiliary_angle_requires_exact_amplitude_and_reviewed_phase(formula):
    from solution_runner.pipelines.equations.exam_trigonometric_sum_identities import (
        compile_identity,
    )

    with pytest.raises(UnsupportedCondition):
        compile_identity(formula, "auxiliary_cosine")


@pytest.mark.parametrize(
    "formula", [r"\sin^3x=0", r"4\cos^3x+\cos^2x=0", r"4\cos^3x+1=0"]
)
def test_triple_cosine_method_rejects_unrelated_polynomials(formula):
    from solution_runner.pipelines.equations.exam_trigonometric_triple_angle import (
        compile_triple,
    )

    with pytest.raises(UnsupportedCondition):
        compile_triple(formula, True)


def test_sum_identity_scales_a_common_angle_and_rejects_a_false_identity_certificate():
    from solution_runner.pipelines.equations.exam_trigonometric_sum_identities import (
        compile_identity,
    )
    from solution_runner.pipelines.equations.exam_trigonometric_sum_product import (
        equation,
    )

    c = case("672798")
    formula = r"\sin(2x+\frac{\pi}{6})+\sin(2x+\frac{\pi}{3})=\sin(2x+\frac{\pi}{4})"
    a = analyze(
        formula,
        r"[-\frac{\pi}{2};\frac{\pi}{2}]",
        (-sp.pi / 2, sp.pi / 2, True, True),
        parent(c),
    )
    assert a.scale == 2 and a.selected == (-sp.Rational(1, 8), sp.Rational(3, 8))
    compiled = compile_identity(formula, "constant_sum")
    with pytest.raises(UnsupportedCondition):
        equation(replace(compiled.sum_product, root=compiled.sum_product.root + 1))
