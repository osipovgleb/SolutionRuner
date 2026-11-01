"""Original variable-log domains, parent methods and selected-only source circles."""

import gzip
import hashlib
import json
import math
import re
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

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
from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
    conditions,
    failed,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_variable.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
ALPHA = sp.acos(R(2, 3)) / sp.pi
EXPECTED = {
    "559574": ((R(1, 3),), (R(1, 3),)),
    "626504": ((R(1, 2) - ALPHA, R(1, 2) + ALPHA), (R(1, 2) + ALPHA,)),
    "650209": (
        (R(1, 6), R(11, 6)),
        (-R(13, 6), -R(11, 6), -R(1, 6), R(1, 6), R(11, 6)),
    ),
    "668195": ((R(5, 6),), (R(5, 6),)),
    "698474": ((R(4, 3), R(11, 6)), (-R(8, 3), -R(13, 6))),
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(c):
    return section(case(c["group"])["context"]["normalized_content"], "solution")[
        "html"
    ]


def analysis(c):
    _, f, i, b = read(c["context"])
    return analyze(f, i, b, parent(c))


def plan(c, context=None, prototype=None):
    h = get_handler(get_group_profile(c["group"]).content_rule_key)
    ctx = context or c["context"]
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
            ctx,
            parent_solution_html=parent(c) if prototype is None else prototype,
            generated_solution_assets=generated,
        )
    )


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def original_zero(key, q):
    si, co = sp.simplify(sp.sin(q * sp.pi)), sp.simplify(sp.cos(q * sp.pi))
    base, arg, target = {
        "559574": (sp.sqrt(2) * si, 1 + co, 2 * si**2),
        "626504": (si, sp.cos(2 * q * sp.pi) - si + 1, si**2),
        "650209": (co, 3 * si**4 + sp.cos(4 * q * sp.pi) + 2, 3 * co**4),
        "668195": (si, sp.sin(2 * q * sp.pi) + 2 * sp.sqrt(3) * si**2 + si, si),
        "698474": (
            -si,
            4 * si**2 - sp.sqrt(3) * sp.sin(2 * q * sp.pi) - 2 * co**2,
            sp.S.One,
        ),
    }[key]
    return (
        base.is_positive is True
        and sp.simplify(base - 1) != 0
        and sp.simplify(arg).is_positive is True
        and sp.simplify(arg - target) == 0
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_follow_original_base_and_argument(c):
    a = analysis(c)
    full, chosen = EXPECTED[c["task"]]
    assert (
        a.scale == 1
        and select(a.series, (0, 2, True, False))[0] == full
        and a.selected == chosen
    )
    assert len(conditions(a)) == 3
    for q in (*full, *chosen):
        assert original_zero(c["task"], q)
    for q in (R(n, 48) for n in range(96)):
        assert original_zero(c["task"], q) == (q in full)
    assert all(failed(a, q) is None for q in full)


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_catalogue_profiles_reuse_the_shared_handler(g):
    p = get_group_profile(g["key"])
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (g["uuid"], g["theme_uuid"], 10, g["order"])
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_are_unused_and_local_replay_preserves_original_inputs(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 999</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    for t in p.transformations:
        key = t["transformation_target_id"]
        items = ctx["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next((s for s in items if s["transformation_target_id"] == key), None)
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, ctx).transformations == () and c["context"] == before
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
    )
    for original in before["normalized_content"]["assets"]:
        assert original in ctx["normalized_content"]["assets"]


@pytest.mark.parametrize("key", ["559574", "650209", "668195"])
def test_unillustrated_methods_do_not_create_or_insert_a_circle(key):
    c = case(key)
    p = plan(c)
    assert not c["context"]["normalized_content"]["assets"]
    assert not BeautifulSoup(p.solution_html, "html.parser").find("img")
    assert (
        get_handler(get_group_profile(key).content_rule_key).diagram_specs(c["context"])
        == ()
    )
    assert analysis(c).selection_method == (
        "inequalities" if key == "650209" else "progressions"
    )


@pytest.mark.parametrize("key", ["626504", "698474"])
def test_source_figures_keep_selected_only_roles_and_original_stage(key):
    c = case(key)
    a = analysis(c)
    asset = c["context"]["normalized_content"]["assets"][0]
    e = CIRCLES[asset["asset_id"]]
    assert e["point_scope"] == "selected"
    assert len(e["green_markers"]) == len(a.selected)
    assert len(e["complete_residues"]) == len(a.residues)
    assert a.image_position == ("outside" if key == "626504" else "after-intro")
    assert len(BeautifulSoup(plan(c).solution_html, "html.parser").find_all("img")) == 1


def test_only_the_misplaced_marker_changes_in_the_corrected_original_svg():
    e = CIRCLES["c2d9286f-f17f-4dda-8dcc-3fbe45013f77"]
    raw = gzip.decompress(
        (DIRECTORY / "c2d9286f-f17f-4dda-8dcc-3fbe45013f77.svgz").read_bytes()
    ).decode()
    svg = (DIRECTORY / e["corrected_file"]).read_text()
    fix = e["correction"]
    assert hashlib.sha256(raw.encode()).hexdigest() == e["sha256"]
    assert hashlib.sha256(svg.encode()).hexdigest() == e["corrected_sha256"]
    assert svg.replace(fix["new_path_d"], fix["old_path_d"]) == raw
    paths = [n.get("d") for n in ET.fromstring(svg).iter() if n.tag.endswith("path")]
    assert fix["new_path_d"] in paths and fix["old_path_d"] not in paths
    assert set(re.findall("[A-Za-z]", fix["new_path_d"])) <= {"M", "C", "L", "Z"}
    coords = list(
        map(
            float, re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", fix["new_path_d"])
        )
    )
    xs, ys = coords[::2], coords[1::2]
    center = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    assert math.dist(center, fix["target"]) < 1e-9
    cx, cy, _ = e["circle"]
    dx, dy = center[0] - cx, cy - center[1]
    radius = math.hypot(dx, dy)
    assert abs(dy / radius - 2 / 3) < 1e-12 and dx < 0
    assert e["green_markers"][0]["inaccurate"] and fix["source_point_error"] > 7


def test_parent_double_angle_and_cotangent_methods_and_arcsine_notation_are_retained():
    f = {key: formulas(plan(case(key)).solution_html) for key in EXPECTED}
    assert any(r"\arcsin" in s for s in f["626504"])
    assert not any(r"\arccos" in s for s in f["626504"])
    assert any(r"\ctg x=" in s for s in f["668195"])
    assert any(r"\ctg2x=" in s for s in f["698474"])
    assert any(r"\cos 2x" in s and "^{2}" in s for s in f["650209"])
    assert any("D=" in s for s in f["559574"])
    assert all("2025" not in s for items in f.values() for s in items)


def test_wrong_parent_interval_length_is_replaced_by_actual_root_selection():
    c = case("668195")
    a = analysis(c)
    html = plan(c).solution_html
    assert a.bounds[1] - a.bounds[0] == R(5, 2)
    assert "1,5" not in html and "1.5" not in html
    assert a.selected == (R(5, 6),)


def test_sine_division_keeps_the_parent_candidate_and_does_not_add_zero_sine_cases():
    c = case("668195")
    a = analysis(c)
    assert a.log_product.equality.variable.candidate_series == ((-R(1, 6), sp.S.One),)
    f = formulas(plan(c).solution_html)
    assert not any(s.startswith(("x=0+", r"x=\pi+")) for s in f)
    nonzero = f.index(r"\sin x\ne0")
    cotangent = next(i for i, s in enumerate(f) if s.startswith(r"\ctg x="))
    assert nonzero < cotangent


def test_original_figure_follows_log_definition_before_lowering_powers():
    c = case("698474")
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    assert soup.img.find_parent("li") is not None
    assert soup.img.find_previous("span", attrs={"data-inline-latex": True})[
        "data-inline-latex"
    ].endswith("^{0}=1")
    assert soup.img.find_next("span", attrs={"data-inline-latex": True})[
        "data-inline-latex"
    ].startswith(r"\sin^2x=")


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_instructions_and_extra_parent_methods_fail_closed(c):
    ctx = deepcopy(c["context"])
    s = section(ctx["normalized_content"], "condition")
    s["html"] = s["html"].replace("Ре\xadши\xadте", "Приближённо решите")
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    with pytest.raises(UnsupportedCondition):
        plan(c, prototype=parent(c) + "<p>Другое решение.</p>")
