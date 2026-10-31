"""Original fraction and ratio domains, mixed numerators and auxiliary methods."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exam_trigonometric import (
    analyze,
    select,
)
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    read,
)

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_fraction_domains.json"
    ).read_text()
)
CASES = DATA["cases"]
X = sp.Symbol("x", real=True)
s, c = sp.sin(X), sp.cos(X)

A = sp.acos(sp.Rational(4, 5)) / sp.pi
B = sp.acos(sp.Rational(3, 5)) / sp.pi
D = sp.atan(sp.Rational(12, 5)) / sp.pi
E = sp.acos(sp.Rational(5, 13)) / sp.pi
SELECTED = {
    "525407": "-59/12 -55/12 -9/2",
    "525452": "-4 -41/12 -37/12 -3",
    "501215": "-5/4",
    "689084": "2 8/3 3",
    "511578": "-5/6 -1/2 1/2",
    "511580": "2 8/3",
    "509606": "11/4",
    "505152": (-3 - A,),
    "511396": (2 + B,),
    "505173": (5 + D,),
    "513346": "8/3",
    "484547": (-2 - E, -sp.Rational(7, 3), -sp.Rational(5, 3)),
    "507689": "",
    "507692": "",
    "511385": "1 5/3",
}
RESIDUES = {
    "525407": "1/12 5/12 1/2 13/12 17/12 3/2",
    "525452": "0 7/12 11/12 1 19/12 23/12",
    "501215": "3/4 7/4",
    "689084": "0 2/3 1",
    "511578": "1/2 7/6 3/2",
    "511580": "0 2/3",
    "509606": "3/4",
    "505152": (1 - A,),
    "511396": (B,),
    "505173": (1 + D,),
    "513346": "2/3",
    "484547": (sp.Rational(1, 3), 2 - E, sp.Rational(5, 3)),
    "507689": "4/3",
    "507692": "5/6",
    "511385": "1 5/3",
}
ORIGINAL = {
    "525407": 4 * sp.sin(X - sp.pi / 2) ** 2 - sp.cot(X),
    "525452": sp.cos(X + sp.pi / 2) ** 2 + sp.tan(X) / 4,
    "501215": 1 + sp.cot(2 * X) - 1 / sp.cos(3 * sp.pi / 2 - 2 * X),
    "689084": (sp.cos(2 * X) + sp.sqrt(3) * s - 1) / (sp.tan(X) - sp.sqrt(3)),
    "511578": (sp.cos(2 * X) + sp.sqrt(3) * c + 1) / (sp.cot(X) + sp.sqrt(3)),
    "511580": (sp.sin(2 * X) - 2 * s - sp.sqrt(3) * c + sp.sqrt(3))
    / (sp.tan(X) - sp.sqrt(3)),
    "509606": (sp.cos(2 * X) + sp.sqrt(2) * c + 1) / (sp.tan(X) - 1),
    "505152": (5 * c + 4) / (4 * sp.tan(X) - 3),
    "511396": (5 * c - 3) / (3 * sp.tan(X) + 4),
    "505173": (5 * sp.tan(X) - 12) / (13 * c - 5),
    "513346": (2 * c + 1) / (sp.tan(X) - sp.sqrt(3)),
    "484547": (26 * c * c - 23 * c + 5) / (13 * s - 12),
    "507689": (2 * s * s + 3 * c) / (2 * s - sp.sqrt(3)),
    "507692": (2 * c * c - 5 * s + 1) / (2 * c - sp.sqrt(3)),
    "511385": (2 * c * c + c - 1) / (2 * s - sp.sqrt(3)),
}
POLES = {
    "525407": (s,),
    "525452": (c,),
    "501215": (sp.sin(2 * X),),
    "689084": (c, s - sp.sqrt(3) * c),
    "511578": (s, c + sp.sqrt(3) * s),
    "511580": (c, s - sp.sqrt(3) * c),
    "509606": (c, s - c),
    "505152": (c, 4 * s - 3 * c),
    "511396": (c, 3 * s + 4 * c),
    "505173": (c, 13 * c - 5),
    "513346": (c, s - sp.sqrt(3) * c),
    "484547": (13 * s - 12,),
    "507689": (2 * s - sp.sqrt(3),),
    "507692": (2 * c - sp.sqrt(3),),
    "511385": (2 * s - sp.sqrt(3),),
}


def allowed(task, q):
    return all(sp.simplify(v.subs(X, q * sp.pi)) != 0 for v in POLES[task])


def expected(value):
    return (
        tuple(map(sp.Rational, value.split()))
        if isinstance(value, str)
        else tuple(map(sp.sympify, value))
    )


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
    ) == (g["uuid"], g["theme_uuid"], 7, g["order"], "14")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_full_and_selected_roots_are_independent_and_respect_original_domain(c):
    task = c["task"]
    a = analysis(c)
    roots = select(a.series, (0, 2, True, False))[0]
    assert roots == expected(RESIDUES[task]) and a.selected == expected(SELECTED[task])
    for q in roots:
        assert allowed(task, q) and sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
    for k in range(24):
        q = sp.Rational(k, 12)
        zero = (
            sp.simplify(ORIGINAL[task].subs(X, q * sp.pi)) == 0
            if allowed(task, q)
            else False
        )
        assert (q in roots) == zero


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


@pytest.mark.parametrize("example", CASES, ids=lambda c: c["task"])
def test_audited_original_figures_keep_every_valid_root_and_original_domain_cross(
    example,
):
    import gzip
    import hashlib
    import math
    from xml.etree import ElementTree as ET

    from bs4 import BeautifulSoup

    from solution_runner.pipelines.equations.exam_trigonometric_auxiliary_figures import (
        validate_system,
    )
    from solution_runner.pipelines.equations.exam_trigonometric_circle import (
        CIRCLES,
        DIRECTORY,
        validate,
    )
    from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
        decode,
        ordered,
    )

    a = analysis(example)
    for asset in example["context"]["normalized_content"]["assets"]:
        aid = asset["asset_id"]
        e = CIRCLES[aid]
        data = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
        assert hashlib.sha256(data).hexdigest() == e["sha256"]
        nodes = list(ET.fromstring(data).iter())
        paths = {n.get("d") for n in nodes}
        multiplier = sp.Rational(e.get("circle_scale", "1"))
        roots = select(
            tuple((q * multiplier, p * multiplier) for q, p in a.series),
            (0, 2, True, False),
        )[0]
        assert ordered(decode(p["angle"]) for p in e["green_markers"]) == roots
        cx, cy, _ = e["circle"]
        for p in e["green_markers"] + e["excluded_markers"]:
            q = decode(p["angle"])
            assert (
                math.hypot(
                    p["x"] - cx - p["radius"] * math.cos(float(q) * math.pi),
                    p["y"] - cy + p["radius"] * math.sin(float(q) * math.pi),
                )
                < 5
            )
            if p in e["green_markers"]:
                assert p["path_d"] in paths and allowed(example["task"], q / multiplier)
            else:
                assert (
                    not allowed(example["task"], q / multiplier) and p["cross_segments"]
                )
                for cross in p["cross_segments"]:
                    assert any(
                        n.tag.endswith(cross["tag"])
                        and all(n.get(k) == v for k, v in cross["attributes"].items())
                        for n in nodes
                    )
        if e.get("figure_kind") == "auxiliary_system":
            validate_system(e, a)
        else:
            validate(e, a)
    specs = get_handler(
        get_group_profile(example["group"]).content_rule_key
    ).diagram_specs(example["context"])
    assert len(specs) == (1 if example["task"] == "501215" else 0)
    assert len(
        BeautifulSoup(plan(example).solution_html, "html.parser").find_all("img")
    ) == (2 if example["task"] == "501215" else 1)


def test_auxiliary_notes_retain_three_methods_and_separate_figure_positions():
    from bs4 import BeautifulSoup

    from solution_runner.pipelines.equations.exam_trigonometric_auxiliary_notes import (
        half_angle,
    )
    from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S

    example = case("501215")
    a = analysis(example)
    assert a.auxiliary_notes and a.scale == 2 and a.raw == S + C + 1 and a.poles == (S,)
    assert a.series == ((-sp.Rational(1, 4), sp.S.One),)
    assert a.branches[0].variable == C and a.branches[0].angle_shift == -sp.Rational(
        1, 4
    )
    raw, branches = half_angle(a)
    assert sp.expand(raw - 2 * C * (S + C)) == 0
    assert {q for b in branches for q in b.residues} == {
        sp.Rational(3, 4),
        sp.Rational(7, 4),
    }
    soup = BeautifulSoup(plan(example).solution_html, "html.parser")
    parts = soup.find("ol").find_all("li", recursive=False)
    assert len(parts[0].find_all("img")) == len(parts[1].find_all("img")) == 1
    text = parts[1].get_text(" ")
    markers = (
        "Примечание 1",
        "синуса суммы",
        "Третий путь",
        "Примечание 2",
        "пересечь",
    )
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions)
    assert "однородному" in text and "красными" in text.lower()
    formulas = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    assert any(r"2 x=" in f and r"\frac{\pi}{2}" in f for f in formulas)


def test_auxiliary_interval_correction_changes_only_six_font_attributes():
    import gzip

    from lxml import etree

    from solution_runner.pipelines.equations.exam_trigonometric_circle import (
        CIRCLES,
        DIRECTORY,
    )

    aid = case("501215")["context"]["normalized_content"]["assets"][0]["asset_id"]
    source = etree.fromstring(
        gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    )
    prepared = etree.fromstring(
        (DIRECTORY / CIRCLES[aid]["corrected_file"]).read_bytes()
    )
    changed = 0
    for before, after in zip(source.iter(), prepared.iter(), strict=True):
        if before.get("font-family") == "'SymbolMT'":
            assert after.get("font-family") == "'Times New Roman'"
            after.set("font-family", "'SymbolMT'")
            changed += 1
    assert changed == 6 and etree.tostring(source) == etree.tostring(prepared)


@pytest.mark.parametrize("task", ["507689", "507692"])
def test_single_fraction_children_keep_only_one_equation_and_its_full_root_circle(task):
    from bs4 import BeautifulSoup

    a = analysis(case(task))
    p = plan(case(task))
    html = BeautifulSoup(p.solution_html, "html.parser")
    assert a.single_part and not a.selected and not a.interval
    assert not html.find("ol") and "а)" not in p.answer and "б)" not in p.answer
    assert "промежут" not in html.get_text() and len(html.find_all("img")) == 1


def test_geometric_note_line_represents_the_same_normalized_system():
    import gzip
    from xml.etree import ElementTree as ET

    from solution_runner.pipelines.equations.exam_trigonometric_circle import (
        CIRCLES,
        DIRECTORY,
    )

    aid = case("501215")["context"]["normalized_content"]["assets"][1]["asset_id"]
    entry = CIRCLES[aid]
    cx, cy, radius = entry["circle"]
    root = ET.fromstring(gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes()))
    lines = [
        n
        for n in root.iter()
        if n.tag.endswith("line")
        and n.get("stroke") == "#007A37"
        and n.get("stroke-dasharray")
    ]
    assert len(lines) == 1
    for end in ("1", "2"):
        x, y = (float(lines[0].get(axis + end)) for axis in ("x", "y"))
        assert abs((x - cx) / radius + (cy - y) / radius + 1) < 0.03
