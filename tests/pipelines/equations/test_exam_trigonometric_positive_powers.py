"""Original powers, parent methods, source circles and local replay for eight groups."""

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
from solution_runner.pipelines.equations.exam_trigonometric import analyze, select
from solution_runner.pipelines.equations.exam_trigonometric_circle import (
    CIRCLES,
    DIRECTORY,
    read,
)
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_power_equality import (
    compile_equality,
)
from solution_runner.pipelines.equations.exam_trigonometric_power_style import (
    figure_stage,
)
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.equations.verified_expression_repair import (
    repair_verified_condition,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_positive_powers.json"
    ).read_text()
)
CASES = DATA["cases"]
FIGURES = {
    a["asset_id"]: CIRCLES[a["asset_id"]]
    for c in CASES
    for a in c["context"]["normalized_content"]["assets"]
}
R = sp.Rational
FONT = "613e8f61-f6ed-48e3-8148-b217960babe1"


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(c):
    return section(case(c["group"])["context"]["normalized_content"], "solution")[
        "html"
    ]


def analysis(c, formula=None):
    fixed, _ = repair_verified_condition(c["context"], validate=read)
    _, f, i, b = read(fixed)
    return analyze(formula or f, i, b, parent(c))


def generated(c, ctx=None):
    h = get_handler(get_group_profile(c["group"]).content_rule_key)
    return tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in h.diagram_specs(ctx or c["context"])
    )


def plan(c, ctx=None, assets=None, prototype=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            ctx or c["context"],
            parent_solution_html=prototype or parent(c),
            generated_solution_assets=generated(c, ctx) if assets is None else assets,
        )
    )


def forms(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def original_value(task, x):
    s, c = mp.sin(x), mp.cos(x)
    power = mp.power
    return {
        "501689": lambda: power(15, c) - power(3, c) * power(5, s),
        "501944": lambda: power(10, s) - power(2, s) * power(5, -c),
        "502293": lambda: power(12, s) - power(4, s) * power(3, -mp.sqrt(3) * c),
        "515743": lambda: power(15, c) - power(3, c) * power(mp.mpf("0.2"), -s),
        "511105": lambda: power(power(49, c), s) - power(7, mp.sqrt(2) * c),
        "501729": lambda: power(power(27, c), s) - power(3, 3 * c / 2),
        "502313": lambda: power(power(25, c), s) - power(5, c),
        "500192": lambda: power(mp.mpf(1) / 81, c) - power(9, 2 * mp.sin(2 * x)),
        "500473": lambda: power(mp.mpf(1) / 49, s) - power(7, 2 * mp.sin(2 * x)),
        "514242": lambda: power(16, s) - power(mp.mpf(1) / 4, 2 * mp.sin(2 * x)),
        "517520": lambda: (
            power(mp.mpf(1) / 9, mp.cos(mp.pi / 2 - x))
            - power(3, 2 * mp.sin(x + mp.pi / 2))
        ),
        "501483": lambda: power(36, mp.sin(2 * x)) - power(6, 2 * s),
        "701886": lambda: power(7, 2 * c) - power(49, mp.sin(2 * x)),
        "701913": lambda: power(mp.mpf(1) / 81, c) - power(9, 2 * mp.sin(2 * x)),
        "508390": lambda: (
            power(5, 2 * mp.sin(2 * x))
            - power(mp.mpf(1) / 25, mp.cos(3 * mp.pi / 2 + x))
        ),
        "528143": lambda: power(power(32, c), s) - 4 * mp.sqrt(2),
        "676803": lambda: power(power(16, s), c) - mp.mpf(1) / 2,
        "676823": lambda: power(power(81, s), c) - mp.mpf(1) / 3,
        "637817": lambda: power(15, s) - power(3, s) * power(5, -c),
        "637846": lambda: power(10, s) - power(5, s) * power(2, c),
    }[task]()


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_full_and_selected_roots_follow_independent_original_powers(c):
    a = analysis(c)
    expected = DATA["expected"][c["task"]]
    full = tuple(map(R, expected["full"]))
    assert select(a.series, (0, 2, True, False))[0] == full
    assert a.selected == tuple(map(R, expected["selected"]))
    with mp.workdps(65):
        for n in range(-192, 193):
            q = R(n, 48)
            x = mp.mpf(int(q.p)) / int(q.q) * mp.pi
            assert (abs(original_value(c["task"], x)) < mp.mpf("1e-45")) == (
                q % 2 in full
            )
    assert a.selection_method == "circle"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_local_replay_preserves_original_assets(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 987654</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    for t in p.transformations:
        target = t["transformation_target_id"]
        if target.startswith("asset:"):
            assert c["task"] == "517520" and t["operation"] == "add"
            ctx["normalized_content"]["assets"].append(t["value"])
        else:
            next(
                s
                for s in ctx["normalized_content"]["sections"]
                if s["transformation_target_id"] == target
            ).update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert (
        ctx["normalized_content"]["assets"][:1]
        == before["normalized_content"]["assets"]
    )
    assert c["context"] == before
    assert len(generated(c)) == (1 if c["task"] == "517520" else 0)
    assert (
        p.condition_html != section(before["normalized_content"], "condition")["html"]
    ) == (c["task"] == "501729")


@pytest.mark.parametrize(
    "aid,e", FIGURES.items(), ids=lambda v: v if isinstance(v, str) else v["task"]
)
def test_original_svg_hash_paths_and_marker_geometry_are_preserved(aid, e):
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    paths = {n.get("d") for n in ET.fromstring(raw).iter() if n.tag.endswith("path")}
    for p in e["green_markers"]:
        assert p["path_d"] in paths
        f = p["native_frame"]
        assert f["path_d"] in paths
        q = float(R(p["angle"])) * math.pi
        assert (
            math.hypot(
                p["x"] - f["cx"] - f["rx"] * math.cos(q),
                p["y"] - f["cy"] + f["ry"] * math.sin(q),
            )
            < 5
        )


@pytest.mark.parametrize(
    "key", ["501689", "637817", "511105", "500192", "501483", "508390"]
)
def test_equal_exponent_parent_method_never_adds_a_ratio_to_one_alternative(key):
    c = case(key)
    a = analysis(c)
    assert a.power_equality.equal_powers is not None
    html = plan(c).solution_html
    assert "равны показатели" in html
    assert "только при нулевом показателе" not in html


@pytest.mark.parametrize(
    "key,base",
    [
        ("500192", 81),
        ("500473", 49),
        ("514242", 16),
        ("517520", 9),
        ("501483", 36),
        ("701886", 49),
        ("701913", 81),
        ("508390", 5),
        ("676803", 2),
        ("676823", 3),
    ],
)
def test_common_base_comes_from_the_actual_child_and_parent_presentation(key, base):
    assert analysis(case(key)).power_equality.equal_powers[0] == base


@pytest.mark.parametrize(
    "key,var",
    [
        ("511105", C),
        ("501729", C),
        ("500192", C),
        ("500473", S),
        ("514242", S),
        ("501483", S),
        ("701886", C),
        ("701913", C),
        ("508390", S),
    ],
)
def test_zero_trig_factor_is_retained_first_before_solving_the_other_factor(key, var):
    a = analysis(case(key))
    assert a.branches[0].polynomial == var
    assert 0 in a.branches[0].values
    assert "D=" not in plan(case(key)).solution_html


@pytest.mark.parametrize(
    "key,level", [("528143", 1), ("676803", -R(1, 2)), ("676823", -R(1, 2))]
)
def test_double_angle_certificate_keeps_original_angle_circles_and_scaled_root_periods(
    key, level
):
    a = analysis(case(key))
    assert a.scale == 2 and a.preferred == S and a.branches[0].values == (level,)
    assert all(p == 1 for _, p in a.series)
    assert (
        CIRCLES[
            case(key)["context"]["normalized_content"]["assets"][0]["asset_id"]
        ].get("circle_scale", "1")
        == "1"
    )
    html = plan(case(key)).solution_html
    assert r"\sin2x=" in html and r"(\sin 2x)" in html


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_figure_subpart_and_derivation_stage_are_preserved(c):
    a = analysis(c)
    assert a.image_position == figure_stage(parent(c))
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    image = soup.find("img")
    part = image.find_parent("li")
    if a.image_position == "outside":
        assert part is None
    else:
        assert part["data-list-marker"] == "а)"
        if a.image_position == "after-steps":
            assert (
                not image.find_next("span", attrs={"data-inline-latex": True})
                or image.find_next(
                    "span", attrs={"data-inline-latex": True}
                ).find_parent("li")
                is not part
            )


def test_portable_minus_fix_changes_only_two_font_families_and_requires_preparation():
    old = ET.fromstring(gzip.decompress((DIRECTORY / (FONT + ".svgz")).read_bytes()))
    new = ET.fromstring((DIRECTORY / CIRCLES[FONT]["corrected_file"]).read_bytes())
    count = 0
    for node in new.iter():
        if node.text == "−" and node.get("font-family") == "'DejaVu Serif'":
            node.set("font-family", "'SymbolMT'")
            count += 1
    for tree in (old, new):
        for node in tree.iter():
            if node.tail is not None and not node.tail.strip():
                node.tail = None
            if node.text is not None and not node.text.strip():
                node.text = None
    assert count == 2 and ET.tostring(old) == ET.tostring(new)
    with pytest.raises(UnsupportedCondition):
        plan(case("517520"), assets=())


def test_identical_child_circle_is_reused_without_a_generated_duplicate():
    a, b = case("676803"), case("676823")
    assert (
        a["context"]["normalized_content"]["assets"]
        == b["context"]["normalized_content"]["assets"]
    )
    assert generated(a) == generated(b) == ()


@pytest.mark.parametrize("key", ["501483", "701886", "701913"])
def test_partial_circle_markers_are_explicitly_selected_roots_not_a_full_root_claim(
    key,
):
    c = case(key)
    a = analysis(c)
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    assert entry["point_scope"] == "selected"
    assert tuple(map(R, entry["residues"])) == tuple(
        sorted({q % 2 for q in a.selected})
    )
    assert len(entry["residues"]) < len(select(a.series, (0, 2, True, False))[0])


@pytest.mark.parametrize("extra", [" ", "<p>Удвойте ответ.</p>"])
def test_damaged_source_restoration_never_applies_to_an_augmented_question(extra):
    c = case("501729")
    ctx = deepcopy(c["context"])
    section(ctx["normalized_content"], "condition")["html"] += extra
    assert repair_verified_condition(ctx, validate=read) == (ctx, None)


@pytest.mark.parametrize("text", ["1\u20602", "-1\u20602"])
def test_word_joiner_is_whitespace_and_cannot_join_two_numeric_operands(text):
    with pytest.raises(UnsupportedCondition):
        ScalarParser(text).parse()


@pytest.mark.parametrize(
    "formula", [r"2^{\sin x}=2^{\cos x}", r"2^{\sin x\cos x+\cos x}=1"]
)
def test_double_angle_method_rejects_a_non_affine_original_exponent(formula):
    with pytest.raises(UnsupportedCondition):
        compile_equality(formula, parent(case("528143")))


def test_unknown_intermediate_figure_and_multiple_double_angle_methods_fail_closed():
    p = parent(case("528143"))
    with pytest.raises(UnsupportedCondition):
        figure_stage(
            p.replace(
                '</li><li data-list-marker="б)">',
                '<span data-inline-latex="x=0"></span></li><li data-list-marker="б)">',
            )
        )
    with pytest.raises(UnsupportedCondition):
        compile_equality(
            r"2^{\sin2x}=1", p + '<span data-inline-latex="\\cos2x=0"></span>'
        )


def test_cosine_double_angle_certificate_is_exact_on_the_complete_unit_circle():
    prototype = parent(case("528143")).replace(r"\sin 2x=1", r"\cos 2x=0")
    e = compile_equality(r"2^{\cos2x}=1", prototype)
    assert e.scale == 2 and e.raw == C
    assert e.power_equality.exponent == 2 * C * C - 1


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_catalog_bindings_share_the_existing_handler(g):
    p = get_group_profile(g["key"])
    assert p.source_group_id == g["uuid"] and p.group_order_index == g["order"]
    assert p.snapshot_theme_id == g["theme_uuid"]
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"
