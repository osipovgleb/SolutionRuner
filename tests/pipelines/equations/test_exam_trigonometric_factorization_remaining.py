"""Complete the factorization theme: cubic identity, circle partition, strict domains."""

import gzip
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path

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
    ordered,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_factorization_remaining.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)
SELECTED = {
    "690532": "-19/6 -17/6 -5/2 -13/6 -11/6 -7/6",
    "691973": "0 1/8 1/4 1/2 5/8 3/4 1",
    "692603": "2/3 3/4 5/4 4/3 5/3 7/4",
    "697397": "-5/4 -3/4",
}
RESIDUES = {
    "690532": "1/6 5/6 7/6 3/2 11/6",
    "691973": "0 1/8 1/4 1/2 5/8 3/4 1 9/8 5/4 3/2 13/8 7/4",
    "692603": "1/4 1/3 2/3 3/4 5/4 4/3 5/3 7/4",
    "697397": "3/4 5/4",
}
ORIGINAL = {
    "690532": 4 * s * s - 2 * c * sp.sin(2 * X) + 3 * s - 1,
    "691973": sp.cos(2 * X) ** 3 - sp.sin(2 * X) ** 3 - sp.cos(2 * X) + sp.sin(2 * X),
    "692603": (1 - sp.cos(8 * X)) * sp.tan(X) - 6 * sp.sin(4 * X) ** 2 * sp.cot(X),
    "697397": sp.cos(3 * X - sp.pi / 2)
    + sp.cos(X + sp.pi / 2)
    + sp.sqrt(2) * sp.sin(2 * X + sp.pi / 2),
}
IDENTITY = {
    "690532": (4 * s * s - 1) * (s + 1),
    "691973": (sp.cos(2 * X) - sp.sin(2 * X)) * sp.sin(4 * X) / 2,
    "692603": 2 * sp.sin(4 * X) ** 2 * (sp.tan(X) - 3 * sp.cot(X)),
    "697397": sp.cos(2 * X) * (2 * s + sp.sqrt(2)),
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
    assert a.selected == tuple(map(sp.sympify, SELECTED[task].split()))
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
def test_complete_roots_obey_original_equation_and_original_domain(c):
    task = c["task"]
    a = analysis(c)
    roots = select(a.series, (0, 2, True, False))[0]
    for k in range(48):
        q = sp.Rational(k, 24)
        angle = q * sp.pi
        allowed = (
            (sp.sin(angle) != 0 and sp.cos(angle) != 0)
            if task == "692603"
            else (sp.cos(angle).is_negative is True)
            if task == "697397"
            else True
        )
        vanishes = sp.simplify(IDENTITY[task].subs(X, angle)) == 0 if allowed else False
        assert (q in roots) == (allowed and vanishes)
    if task == "697397":
        assert a.domain == -C and a.strict_domain and a.angle_product is not None
        assert a.series == (
            (sp.Rational(3, 4), sp.Integer(2)),
            (sp.Rational(5, 4), sp.Integer(2)),
        )
        assert all(sp.cos(q * sp.pi).is_negative for q in roots)
    if task == "692603":
        assert a.poles == (S, C) and a.alternative is not None
        assert select(a.alternative.series, (0, 2, True, False))[0] == roots


def test_difference_of_cubes_merges_only_the_zero_product_by_double_angle():
    c = case("691973")
    a = analysis(c)
    html = plan(c).solution_html
    assert len(a.branches) == 2 and a.branches[1].angle_scale == 2
    assert a.series == (
        (sp.Rational(1, 8), sp.Rational(1, 2)),
        (sp.S.Zero, sp.Rational(1, 4)),
    )
    assert (
        "разности кубов" in html
        and "двойного угла" in html
        and "суммы кубов" not in html
    )
    assert (
        html.index("разности кубов")
        < html.index("двойного угла")
        < html.index("Решим оба уравнения")
    )
    formulas = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert any(r"\sin(4 x)" in f for f in formulas)
    assert html.count("целого параметра каждой серии") == 1


def test_partition_keeps_two_original_figures_in_part_b_and_every_endpoint():
    from solution_runner.pipelines.equations.exam_trigonometric_panels import sources

    c = case("690532")
    a = analysis(c)
    panels = sources(c["context"])
    html = BeautifulSoup(plan(c).solution_html, "html.parser")
    assert a.image_position == "selection" and len(panels) == 2
    assert not html.select('li[data-list-marker="а)"] img')
    images = html.select(
        'li[data-list-marker="б)"] section[data-layout="media-row"] img'
    )
    assert [i["data-asset-key"] for i in images] == ["image_1", "image_2"]
    assert [e["labels"] for _, e in panels] == [
        ["-19/6", "-17/6", "-5/2", "-13/6", "-11/6"],
        ["-7/6"],
    ]
    assert panels[0][1]["bounds"][2:] == [False, False] and panels[1][1]["bounds"][
        2:
    ] == [True, False]
    transformed = next(
        t
        for t in plan(c).transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert transformed["value"]["asset_keys"] == ["image_1", "image_2"]


@pytest.mark.parametrize("task", ["690532", "692603", "697397"])
def test_audited_figures_keep_exact_bytes_and_markers_include_open_root(task):
    from xml.etree import ElementTree as ET

    c = case(task)
    a = analysis(c)
    for asset in c["context"]["normalized_content"]["assets"]:
        aid = asset["asset_id"]
        e = CIRCLES[aid]
        svg = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
        assert hashlib.sha256(svg).hexdigest() == e["sha256"]
        paths = {
            n.get("d"): n for n in ET.fromstring(svg).iter() if n.tag.endswith("path")
        }
        points = e["green_markers"] + e.get("open_markers", [])
        assert ordered(sp.Rational(m["angle"]) for m in points) == tuple(
            map(sp.Rational, e["residues"])
        )
        cx, cy, _ = e["circle"]
        for point in points:
            assert point["path_d"] in paths
            angle = float(sp.Rational(point["angle"])) * math.pi
            assert (
                math.hypot(
                    point["x"] - cx - point["radius"] * math.cos(angle),
                    point["y"] - cy + point["radius"] * math.sin(angle),
                )
                < 2
            )
        if e.get("panel_index") == 1:
            marker = e["open_markers"][0]
            node = paths[marker["path_d"]]
            assert (
                marker["angle"] == "7/6"
                and node.get("fill") == "#FFEEE9"
                and node.get("stroke") == "#00487E"
            )
            assert -sp.Rational(5, 6) not in a.selected
        elif not e.get("partition_bounds"):
            validate(e, a)


@pytest.mark.parametrize(
    "mutation", ["missing", "order", "gap", "overlap", "outer", "roots", "extra"]
)
def test_unknown_or_incomplete_circle_partition_fails_closed(mutation, monkeypatch):
    from solution_runner.pipelines.equations.exam_trigonometric_circle import (
        CIRCLES as registry,
    )

    c = deepcopy(case("690532"))
    assets = c["context"]["normalized_content"]["assets"]
    if mutation == "missing":
        assets.pop()
    elif mutation == "order":
        assets.reverse()
    elif mutation == "extra":
        assets.append(deepcopy(assets[0]))
    else:
        aid = assets[1]["asset_id"]
        entry = deepcopy(registry[aid])
        if mutation == "gap":
            entry["bounds"][0] = "-4/3"
        elif mutation == "overlap":
            entry["bounds"][0] = "-5/3"
        elif mutation == "outer":
            entry["partition_bounds"][1] = "-1"
        else:
            entry["labels"] = ["-5/6"]
        monkeypatch.setitem(registry, aid, entry)
    with pytest.raises(UnsupportedCondition):
        plan(c)


@pytest.mark.parametrize("angle", [2, 3, 6])
def test_ratio_product_extends_both_methods_to_related_angles_without_losing_poles(
    angle,
):
    from solution_runner.pipelines.equations.exam_trigonometric_ratio_product import (
        branches,
        compile_product,
        series,
    )

    solutions = []
    for method in ("multiply", "factor"):
        eq = compile_product(
            r"(1-\cos "
            + str(2 * angle)
            + r"x)\tg x=6\sin^{2} "
            + str(angle)
            + r"x\ctg x",
            method,
        )
        solutions.append(
            select(series(branches(eq.ratio_product)), (0, 2, True, False))[0]
        )
    assert solutions[0] == solutions[1]
    for k in range(48):
        q = sp.Rational(k, 24)
        allowed = sp.sin(q * sp.pi) != 0 and sp.cos(q * sp.pi) != 0
        zero = (
            sp.simplify(sp.sin(angle * q * sp.pi) ** 2 * (sp.tan(q * sp.pi) ** 2 - 3))
            == 0
            if allowed
            else False
        )
        assert (q in solutions[0]) == (allowed and zero)


@pytest.mark.parametrize(
    "formula",
    [
        r"(1-\cos 7x)\tg x=6\sin^{2} 4x\ctg x",
        r"(1-\cos 8x)\tg(2x)=6\sin^{2} 4x\ctg x",
        r"(1-\cos 8x)\tg x=-6\sin^{2} 4x\ctg x",
        r"(1-\cos 8x)\tg x=6\sin^{2} 4x\ctg x+1",
        r"(1-\cos 8x)\tg x=6\sin^{2} 4x\ctg x/\cos x",
        r"(1-\cos 10x)\tg x=6\sin^{2} 5x\ctg x",
    ],
)
def test_unreviewed_ratio_identity_angles_domains_or_terms_fail_closed(formula):
    from solution_runner.pipelines.equations.exam_trigonometric_ratio_product import (
        compile_product,
    )

    with pytest.raises(UnsupportedCondition):
        compile_product(formula, "multiply")


@pytest.mark.parametrize(
    "radicand", [r"1-\cos x", r"-\cos^2x", r"-\cos2x", r"-\sin x\cos x"]
)
def test_unreviewed_radical_denominator_does_not_borrow_a_plausible_circle(radicand):
    from solution_runner.pipelines.equations.exam_trigonometric_radical_quotient import (
        compile_quotient,
    )

    with pytest.raises(UnsupportedCondition):
        compile_quotient(
            r"\frac{\sin3x-\sin x+\sqrt2\cos2x}{\sqrt{" + radicand + r"}}=0",
            product=True,
        )


def test_strict_domain_is_explained_after_summing_numerator_and_before_final_series():
    html = plan(case("697397")).solution_html
    assert "определён и отличен от нуля" in html
    assert html.index("строгому условию") < html.index(
        "После отбора по области определения"
    )
    assert "формулу суммы" in html
    assert not BeautifulSoup(html, "html.parser").find(
        "img", {"data-asset-key": "exam_trig_circle"}
    )


def test_related_sum_of_cubes_keeps_its_sign_and_double_angle():
    from solution_runner.pipelines.equations.exam_trigonometric_proof import first

    a = analyze(
        r"\cos^{3} 2x+\sin^{3} 2x=\cos2x+\sin2x",
        "[0;\\pi]",
        (0, sp.pi, True, True),
        parent(case("691973")),
    )
    assert a.series == (
        (-sp.Rational(1, 8), sp.Rational(1, 2)),
        (sp.S.Zero, sp.Rational(1, 4)),
    )
    intro, html = first(a)
    assert "суммы кубов" in html and "разности кубов" not in intro + html
    assert "двойного угла" in html
