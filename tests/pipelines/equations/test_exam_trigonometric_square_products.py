"""Complete squares, independent angle factors, and tangent grouping."""

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
from solution_runner.pipelines.equations.exam_trigonometric_angle_product import (
    compile_product,
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
from solution_runner.pipelines.equations.exam_trigonometric_square_factor import square
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_square_products.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
SELECTED = {
    "563557": "-9/4 -2 -1",
    "563594": "3/2 5/2 17/6",
    "563574": "-13/4 -3 -2",
    "563547": "-3 -2 -5/3",
    "563613": "13/6 5/2 7/2",
    "563632": "7/4 2 3",
    "563678": "-4 -15/4 -3",
    "563653": "-4 -15/4 -3",
    "563671": "-3 -13/6 -2",
    "563731": "2 5/2 3",
    "563895": "-5/2 -7/3 -3/2",
    "563916": "5/2 8/3 7/2",
    "625650": "-7/4 -4/3 -5/4",
    "628366": "-9/4 -5/4 -1",
    "628484": "-4 -15/4 -11/4",
    "630126": "17/6 11/3",
    "630162": "-23/6 -11/3 -19/6",
    "630265": "-11/3 -17/6",
    "632649": "7 23/3 47/6 8",
    "633181": "-1 -5/6 -2/3 0 1/6 1/3",
}
RESIDUES = {
    "563557": "0 1 5/4 7/4",
    "563594": "1/2 5/6 7/6 3/2",
    "563574": "0 1/4 3/4 1",
    "563547": "0 1/3 2/3 1",
    "563613": "1/6 1/2 3/2 11/6",
    "563632": "0 1 5/4 7/4",
    "563678": "0 1/4 1 7/4",
    "563653": "0 1/4 1 7/4",
    "563671": "0 1/6 1 11/6",
    "563731": "0 1/2 1",
    "563895": "1/2 4/3 3/2 5/3",
    "563916": "1/3 1/2 2/3 3/2",
    "625650": "1/4 2/3 3/4 5/4 4/3 7/4",
    "628366": "3/4 1 7/4",
    "628484": "0 1/4 5/4",
    "630126": "1/6 1/3 5/6 5/3",
    "630162": "1/6 1/3 5/6 5/3",
    "630265": "1/3 7/6 5/3 11/6",
    "632649": "0 2/3 5/6 1 5/3 11/6",
    "633181": "0 1/6 1/3 1 7/6 4/3",
}
ORIGINAL = {
    "563557": 2 * s**3 + s + 2 * sp.sqrt(2) - 2 * sp.sqrt(2) * c**2,
    "563594": 4 * c**3 + 3 * c + 4 * sp.sqrt(3) - 4 * sp.sqrt(3) * s**2,
    "563574": 2 * s**3 + sp.sqrt(2) * sp.cos(2 * X) + s - sp.sqrt(2),
    "563547": 4 * s**3 + 2 * sp.sqrt(3) * sp.cos(2 * X) + 3 * s - 2 * sp.sqrt(3),
    "563613": 4 * c**3 - 2 * sp.sqrt(3) * sp.cos(2 * X) + 3 * c - 2 * sp.sqrt(3),
    "563632": 2 * s**3 - sp.sqrt(2) * sp.cos(2 * X) + s + sp.sqrt(2),
    "563678": 2 * s * c**2 - sp.sqrt(2) * sp.sin(2 * X) + s,
    "563653": 2 * s * c**2 - sp.sqrt(2) * sp.sin(2 * X) + s,
    "563671": 4 * s * c**2 - 2 * sp.sqrt(3) * sp.sin(2 * X) + 3 * s,
    "563731": s**3 + sp.cos(2 * X) + s - 1,
    "563895": 7 * sp.sin(sp.pi / 2 + X) + 4 * sp.sqrt(3) * s * c - 4 * c**3,
    "563916": 7 * sp.sin(sp.pi / 2 - X) - 4 * sp.sqrt(3) * s * c - 4 * c**3,
    "625650": 2 * c**2 + sp.cos(3 * X) - 1 - sp.sin(3 * sp.pi / 2 - X),
    "628366": sp.tan(X) + s + c + 1,
    "628484": sp.tan(X) - s + c - 1,
    "630126": 2 * sp.sin(2 * X) + 2 * sp.sin(-X) - 2 * sp.cos(-X) + 1,
    "630162": 2 * sp.sin(2 * X) + 2 * sp.sin(-X) - 2 * sp.cos(-X) + 1,
    "630265": 2 * sp.sin(2 * X) + 2 * sp.sin(-X) + 2 * sp.cos(-X) - 1,
    "632649": sp.sin(3 * X - 3 * sp.pi / 2)
    + sp.sin(X + 7 * sp.pi / 2)
    - sp.sqrt(3) * sp.cos(X + 3 * sp.pi / 2),
    "633181": (1 - sp.cos(2 * X)) * sp.sin(2 * X) - sp.sqrt(3) * s**2,
}
IDENTITY = {
    "563557": s * (sp.sqrt(2) * s + 1) ** 2,
    "563594": c * (2 * c + sp.sqrt(3)) ** 2,
    "563574": s * (sp.sqrt(2) * s - 1) ** 2,
    "563547": s * (2 * s - sp.sqrt(3)) ** 2,
    "563613": c * (2 * c - sp.sqrt(3)) ** 2,
    "563632": s * (sp.sqrt(2) * s + 1) ** 2,
    "563678": s * (sp.sqrt(2) * c - 1) ** 2,
    "563653": s * (sp.sqrt(2) * c - 1) ** 2,
    "563671": s * (2 * c - sp.sqrt(3)) ** 2,
    "563731": s * (s - 1) ** 2,
    "563895": c * (2 * s + sp.sqrt(3)) ** 2,
    "563916": c * (2 * s - sp.sqrt(3)) ** 2,
    "625650": sp.cos(2 * X) * (1 + 2 * c),
    "628366": (c + 1) * (sp.tan(X) + 1),
    "628484": (c - 1) * (1 - sp.tan(X)),
    "630126": (2 * c - 1) * (2 * s - 1),
    "630162": (2 * c - 1) * (2 * s - 1),
    "630265": (2 * c - 1) * (2 * s + 1),
    "632649": -s * (2 * sp.sin(2 * X) + sp.sqrt(3)),
    "633181": (1 - sp.cos(2 * X)) * (sp.sin(2 * X) - sp.sqrt(3) / 2),
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
    assert sp.trigsimp(sp.expand_trig(ORIGINAL[task] - IDENTITY[task])) == 0
    assert a.selected == tuple(map(sp.Rational, SELECTED[task].split()))
    assert select(a.series, (0, 2, True, False))[0] == tuple(
        map(sp.Rational, RESIDUES[task].split())
    )
    for q in a.selected:
        assert sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0


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
def test_source_geometry_hashes_and_figure_preparation_are_exact(c):
    a = analysis(c)
    assets = c["context"]["normalized_content"]["assets"]
    specs = get_handler(get_group_profile(c["group"]).content_rule_key).diagram_specs(
        c["context"]
    )
    assert bool(specs) == (c["task"] in ("630162", "630265"))
    if assets:
        asset = assets[0]["asset_id"]
        entry = CIRCLES[asset]
        assert (
            hashlib.sha256(
                gzip.decompress((DIRECTORY / (asset + ".svgz")).read_bytes())
            ).hexdigest()
            == entry["sha256"]
        )
    else:
        entry = recipe(c["context"])
        if c["task"] == "563731":
            assert entry is None and a.selection_method == "progressions"
            return
    validate(entry, a)
    expected = (
        ordered(turn(q) for q in a.selected)
        if entry.get("point_scope") == "selected"
        else a.residues
    )
    assert tuple(map(decode, entry["residues"])) == expected
    p = plan(c)
    assert len(BeautifulSoup(p.solution_html, "html.parser").find_all("img")) == bool(
        assets or specs
    )


@pytest.mark.parametrize(
    "task",
    [
        "563557",
        "563594",
        "563574",
        "563547",
        "563613",
        "563632",
        "563678",
        "563653",
        "563671",
        "563731",
        "563895",
        "563916",
    ],
)
def test_full_square_keeps_zero_branch_and_avoids_unneeded_discriminant(task):
    a = analysis(case(task))
    assert a.series[0][1] == 1
    assert any(b.square_factor for b in a.branches)
    html = plan(case(task)).solution_html
    assert "полный квадрат" in html
    assert ("D=" in html) == (task in ("563557", "563594"))


@pytest.mark.parametrize("task", ["563613", "563731", "563895", "563916"])
def test_parent_length_argument_keeps_its_optional_single_circle(task):
    a = analysis(case(task))
    assert a.selection_method == "progressions"
    html = plan(case(task)).solution_html
    assert "длина" in BeautifulSoup(html, "html.parser").get_text().lower()
    assert "не превосходит" in html


@pytest.mark.parametrize("task", ["625650", "632649", "633181"])
def test_each_angle_factor_uses_its_own_period(task):
    a = analysis(case(task))
    assert a.angle_product is not None
    assert {b.angle_scale for b in a.branches} == ({2} if task == "633181" else {1, 2})
    assert "со своим углом" in plan(case(task)).solution_html
    assert all(sp.simplify(ORIGINAL[task].subs(X, sp.pi * q)) == 0 for q in a.residues)


@pytest.mark.parametrize("task,cosine", [("628366", -1), ("628484", 1)])
def test_tangent_grouping_keeps_cosine_branch_on_original_domain(task, cosine):
    a = analysis(case(task))
    assert a.poles == (C,)
    assert a.branches[0].variable.name == "tangent"
    assert any(cosine in b.values for b in a.branches if b.variable == C)
    html = plan(case(task)).solution_html
    assert r"\cos x\ne0" in html and r"\sin x=\cos x\cdot\tg x" in html
    assert all(sp.cos(q * sp.pi) != 0 for q in a.residues)


def test_prepared_child_circle_matches_three_selected_points_and_full_certificate():
    c = case("630162")
    entry = recipe(c["context"])
    root = ET.fromstring((DIRECTORY / entry["file"]).read_text())
    marks = root.findall('.//*[@data-role="selected-root"]')
    assert {m.get("data-root") for m in marks} == {"-23/6", "-11/3", "-19/6"}
    for m in marks:
        q = float(m.get("data-angle"))
        assert float(m.get("cx")) == pytest.approx(
            115 + 72 * math.cos(q * math.pi), abs=1e-7
        )
        assert float(m.get("cy")) == pytest.approx(
            120 - 72 * math.sin(q * math.pi), abs=1e-7
        )
    assert (
        root.find('.//*[@data-role="interval-arc"]').get("d")
        == "M187 120 A72 72 0 1 0 115 192"
    )
    assert len(root.findall('.//*[@data-role="projection"]')) == 1
    assert set(entry["complete_residues"]) - set(entry["residues"]) == {"5/3"}
    with pytest.raises(UnsupportedCondition):
        validate(entry, replace(analysis(c), residues=analysis(c).residues[:-1]))


def test_inaccurate_source_marker_is_corrected_locally_without_rewriting_source():
    c = case("630265")
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    root = ET.fromstring((DIRECTORY / entry["corrected_file"]).read_text())
    points = root.findall('.//*[@data-corrected-angle="7/6"]')
    assert len(points) == 2
    old = next(m for m in entry["green_markers"] if m["angle"] == "7/6")
    assert old["inaccurate"]
    for point in points:
        dx, dy = map(float, re.findall(r"[-\d.]+", point.get("transform")))
        assert old["x"] + dx == pytest.approx(
            103 + 62.5 * math.cos(7 * math.pi / 6), abs=1e-7
        )
        assert old["y"] + dy == pytest.approx(
            86.2 - 62.5 * math.sin(7 * math.pi / 6), abs=1e-7
        )


@pytest.mark.parametrize(
    "formula",
    [
        r"\sin x=0",
        r"\sin 13x\cos x=0",
        r"\sin x\cos x\sin2x=0",
        r"\sin x\cos(x/2)=0",
        r"\tg x\sin2x=0",
        r"\sin x\cos2x=1",
    ],
)
def test_unreviewed_or_unbounded_angle_products_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compile_product(formula)


@pytest.mark.parametrize("polynomial", [S * S + 1, S * S + S + 1, S**3, S, sp.S.Zero])
def test_non_square_polynomials_cannot_be_presented_as_complete_squares(polynomial):
    assert square(polynomial, S) is None
