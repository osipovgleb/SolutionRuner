"""Exact log definitions, parent methods and independently audited source frames."""

import gzip
import hashlib
import json
import math
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
from solution_runner.pipelines.equations.exam_trigonometric_compile import C, S
from solution_runner.pipelines.equations.exam_trigonometric_inverse import (
    compare_q,
    decode,
)
from solution_runner.pipelines.equations.exam_trigonometric_log_product import (
    conditions,
    failed,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_14_trigonometric_log_equalities.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
ALPHA = sp.acos(sp.sqrt(2) / 4) / sp.pi
EXPECTED = {
    "517509": (
        (R(1, 2), R(4, 3), R(3, 2), R(5, 3)),
        (-R(1, 2), -R(1, 3), R(1, 2), R(4, 3), R(3, 2)),
    ),
    "517511": ((R(1, 4), R(3, 4)), (-R(7, 4), -R(5, 4))),
    "639695": ((R(1, 2), R(4, 3), R(3, 2), R(5, 3)), (R(5, 2), R(10, 3), R(7, 2))),
    "639751": ((R(5, 6), R(7, 6)), (R(17, 6), R(19, 6))),
    "531021": ((R(1, 4), R(3, 4)), (-R(5, 4), R(1, 4))),
    "641159": ((R(1, 4), R(3, 4)), (-R(7, 4), -R(5, 4))),
    "547764": (
        (R(1, 2), R(4, 3), R(3, 2), R(5, 3)),
        (R(4, 3), R(3, 2), R(5, 3), R(5, 2), R(10, 3), R(7, 2)),
    ),
    "639482": ((0, R(3, 4), 1, R(5, 4)), (1, R(5, 4), 2)),
    "639648": ((0, R(2, 3), 1, R(4, 3)), (-R(10, 3), -3, -R(8, 3), -2)),
    "639688": ((0, 1 - ALPHA, 1, 1 + ALPHA), (1, 1 + ALPHA, 2)),
    "691277": ((R(1, 6), R(11, 6)), (R(35, 6), R(37, 6))),
    "697406": ((R(1, 4),), (R(1, 4),)),
    "697407": ((R(1, 3),), (-R(5, 3),)),
}
POLYNOMIALS = {
    "517509": -sp.sqrt(3) * C - 2 * S * C,
    "639695": -sp.sqrt(3) * C - 2 * S * C,
    "547764": -sp.sqrt(3) * C - 2 * S * C,
    "517511": 5 * sp.sqrt(2) * S - 6 * C * C - 2,
    "531021": 5 * sp.sqrt(2) * S - 6 * C * C - 2,
    "641159": 5 * sp.sqrt(2) * S - 6 * C * C - 2,
    "639751": -sp.sqrt(3) * C - 6 * S * S,
    "639482": sp.sqrt(2) * S + 2 * S * C,
    "639648": S + 2 * S * C,
    "639688": sp.sqrt(2) * S + 4 * S * C,
    "691277": 2 * C * C - (sp.sqrt(3) + 12) * C + 6 * sp.sqrt(3),
    "697406": 2 * S * C - sp.sqrt(2) * C,
    "697407": 2 * S * C - sp.sqrt(3) * C,
}


def case(key):
    return next(c for c in CASES if c["task"] == key)


def parent(c):
    return section(case(c["group"])["context"]["normalized_content"], "solution")[
        "html"
    ]


def analysis(c, context=None):
    _, f, i, b = read(context or c["context"])
    return analyze(f, i, b, parent(c))


def generated(c, context=None):
    h = get_handler(get_group_profile(c["group"]).content_rule_key)
    return tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in h.diagram_specs(context or c["context"])
    )


def plan(c, context=None, assets=None, prototype=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent(c) if prototype is None else prototype,
            generated_solution_assets=generated(c, context)
            if assets is None
            else assets,
        )
    )


def formulas(html):
    return [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def original_zero(key, q):
    si, co = sp.simplify(sp.sin(q * sp.pi)), sp.simplify(sp.cos(q * sp.pi))
    value = sp.simplify(POLYNOMIALS[key].subs({S: si, C: co}))
    if key in ("697406", "697407"):
        return (
            value == 0 and (2 * si * co).is_positive is True and co.is_positive is True
        )
    # log_b(b^x+P)=x iff P=0, and log_3(81+P)=4 iff P=0.
    # This exact equivalence avoids loss of P when b^x is very large.
    return value == 0


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_follow_the_original_log_definitions(c):
    a = analysis(c)
    full, chosen = EXPECTED[c["task"]]
    assert select(a.series, (0, 2, True, False))[0] == full and a.selected == chosen
    for q in (*full, *chosen):
        assert original_zero(c["task"], sp.sympify(q))
    for q in (R(n, 24) for n in range(48)):
        assert original_zero(c["task"], q) == any(sp.simplify(q - v) == 0 for v in full)


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_exact_profiles_extend_the_existing_shared_runner(g):
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
    section(ctx["normalized_content"], "answer")["html"] = "<p>Wrong saved answer</p>"
    section(ctx["normalized_content"], "solution")["html"] = (
        "<p>Unused stored child solution</p>"
    )
    p = plan(c, ctx)
    assert p == plan(c)
    for t in p.transformations:
        key = t["transformation_target_id"]
        items = ctx["normalized_content"][
            "assets" if key.startswith("asset:") else "sections"
        ]
        item = next(
            (i for i in items if i.get("transformation_target_id") == key), None
        )
        if item is None:
            item = {"transformation_target_id": key}
            items.append(item)
        item.update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert (
        ctx["normalized_content"]["assets"][
            : len(before["normalized_content"]["assets"])
        ]
        == before["normalized_content"]["assets"]
    )
    assert section(ctx["normalized_content"], "condition") == section(
        before["normalized_content"], "condition"
    )
    assert c["context"] == before


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_native_source_paths_frames_and_all_root_and_boundary_markers_are_certified(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
    root = ET.fromstring(raw)
    paths = {n.get("d") for n in root.iter() if n.tag.endswith("path")}
    for frame in entry["native_frames"]:
        assert frame["path_d"] in paths
    a = analysis(c)
    for m in (*entry["green_markers"], *entry["boundary_markers"]):
        assert m["path_d"] in paths
        frame = entry["native_frames"][m["native_frame"]]
        q = decode(m["angle"])
        angle = float(q) * math.pi
        distance = math.hypot(
            m["x"] - frame["cx"] - frame["rx"] * math.cos(angle),
            m["y"] - frame["cy"] + frame["ry"] * math.sin(angle),
        )
        if m.get("inaccurate"):
            assert distance > 5 and entry["corrected_file"]
        else:
            assert distance < 5
        if m in entry["green_markers"]:
            assert original_zero(c["task"], q)
        else:
            assert any(compare_q(q, b % 2) == 0 for b in a.bounds[:2])


def test_extra_quarter_turn_uses_native_ellipse_axes_without_fitting_to_root_markers():
    c = case("517509")
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    frame = next(f for f in entry["native_frames"] if f["stroke"] == "#003686")
    assert frame["path_d"] == "M7.191,127.721  c0,46.921,33.145,84.96,74.035,84.96"
    assert frame["cx"] == pytest.approx(7.191 + 74.035) and frame["cy"] == 127.721
    assert (frame["rx"], frame["ry"]) == pytest.approx((74.035, 84.96), abs=1e-12)
    assert any(
        m["native_frame"] == entry["native_frames"].index(frame)
        for m in entry["green_markers"]
    )


@pytest.mark.parametrize("key", ["639482", "639688"])
def test_only_wrong_marker_contours_guide_and_required_label_clearance_are_changed(key):
    c = case(key)
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    model = entry["correction"]
    original = ET.fromstring(
        gzip.decompress(
            (
                DIRECTORY
                / (
                    c["context"]["normalized_content"]["assets"][0]["asset_id"]
                    + ".svgz"
                )
            ).read_bytes()
        )
    )
    raw = (DIRECTORY / entry["corrected_file"]).read_bytes()
    corrected = ET.fromstring(raw)
    assert hashlib.sha256(raw).hexdigest() == entry["corrected_sha256"]
    old = list(original.iter())
    new = list(corrected.iter())
    assert len(old) == len(new)
    changes = []
    for a, b in zip(old, new, strict=True):
        assert a.tag == b.tag and a.text == b.text and a.tail == b.tail
        if a.attrib == b.attrib:
            continue
        changes.append(a.tag.split("}")[-1])
        aa, bb = dict(a.attrib), dict(b.attrib)
        if a.tag.endswith("path"):
            assert {"old": aa.pop("d"), "new": bb.pop("d")} in model[
                "paths"
            ] and aa == bb
        elif a.tag.endswith("line"):
            assert aa == model["guide_before"] and bb == model["guide_after"]
        else:
            assert (
                key == "639688"
                and a.tag.endswith("g")
                and not aa
                and bb == {"transform": "translate(0 5)"}
            )
    assert sorted(changes) == (
        ["g", "line", "path", "path"] if key == "639688" else ["line", "path", "path"]
    )
    frame = next(
        f for f in entry["native_frames"] if f["path_d"] == entry["native_circle_path"]
    )
    q = R(5, 4) if key == "639482" else 1 + ALPHA
    target = model["target"]
    assert target == pytest.approx(
        [
            frame["cx"] + frame["rx"] * math.cos(float(q) * math.pi),
            frame["cy"] - frame["ry"] * math.sin(float(q) * math.pi),
        ],
        abs=1e-7,
    )
    assert (
        float(model["guide_after"]["x1"])
        == float(model["guide_after"]["x2"])
        == pytest.approx(target[0])
    )
    assert float(model["guide_after"]["y2"]) < target[1]


def test_missing_minus_is_outlined_without_changing_any_other_source_byte():
    c = case("531021")
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[aid]
    model = entry["correction"]
    original = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes()).decode()
    fixed = (DIRECTORY / entry["corrected_file"]).read_text()
    assert original.count(model["old_node"]) == 1 and fixed == original.replace(
        model["old_node"], model["new_node"]
    )
    assert (
        "outlined-math-minus" in model["new_node"]
        and "font-family" not in model["new_node"]
    )
    assert hashlib.sha256(fixed.encode()).hexdigest() == entry["corrected_sha256"]


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_figures_remain_in_the_parent_subpart_and_only_three_corrections_are_prepared(
    c,
):
    p = plan(c)
    soup = BeautifulSoup(p.solution_html, "html.parser")
    image = soup.find("img")
    part = image.find_parent("li")
    corrected = c["task"] in ("531021", "639482", "639688")
    assert len(generated(c)) == int(corrected)
    assert image["data-asset-key"] == ("exam_trig_circle" if corrected else "image_1")
    if c["group"] in ("547764", "691277", "697406"):
        assert part is None and str(soup).index("<img") < str(soup).index("<ol")
    else:
        assert part["data-list-marker"] == "а)"
    if c["group"] == "531021":
        before = str(part).split("<img")[0]
        after = str(part).split("<img")[1]
        assert "D=" not in before and r"\sin x" in before and "D=" in after
    elif part is not None:
        assert str(part).index("<img") < str(part).index("Преобразуем исходное")


def test_grouping_and_parent_candidate_order_are_retained_without_an_invented_discriminant():
    c = case("691277")
    a = analysis(c)
    html = plan(c).solution_html
    f = formulas(html)
    assert (
        a.log_product.equality.grouping
        and "Сгруппируем" in html
        and not any(x.startswith("D=") for x in f)
    )
    levels = [x for x in f if x.startswith(r"(\cos x)=")]
    assert levels[0].endswith("6")
    assert a.series == ((-R(1, 6), 2), (R(1, 6), 2))


def test_parent_n_and_sine_first_family_order_survive_changed_child_coefficients():
    for key in ("517511", "639751"):
        a = analysis(case(key))
        assert a.parameter == "n" and r"n\in\mathbb Z" in plan(case(key)).answer
    assert analysis(case("639648")).series[0] == (0, 1)


@pytest.mark.parametrize("key", ["697406", "697407"])
def test_both_positive_arguments_prove_cosine_nonzero_before_dividing(key):
    c = case(key)
    a = analysis(c)
    assert (
        a.log_product.divide == C
        and len(conditions(a)) == 2
        and len(a.branches) == 1
        and a.branches[0].variable == S
    )
    assert failed(a, R(1, 2)) is not None and failed(a, R(3, 2)) is not None
    assert failed(a, R(3, 4) if key == "697406" else R(2, 3)) is not None
    html = plan(c).solution_html
    assert (
        html.index("положительность обоих")
        < html.index("cos x\\ne0")
        < html.index("разделим на него")
    )


def test_inverse_cosine_and_closed_blue_boundary_root_are_exact_and_not_lost():
    c = case("639688")
    a = analysis(c)
    assert compare_q(ALPHA, R(1, 3)) > 0 and compare_q(ALPHA, R(1, 2)) < 0
    assert a.selected == (1, 1 + ALPHA, 2) and a.series[-1] == (-1 + ALPHA, 2)
    entry = CIRCLES[c["context"]["normalized_content"]["assets"][0]["asset_id"]]
    assert any(
        decode(m["angle"]) == 1 and m["fill"] == "#00487E"
        for m in entry["green_markers"]
    )
    assert r"\arccos" in plan(c).answer and r"\sqrt{2}" in plan(c).answer


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_assets_extra_instructions_changed_bounds_and_forged_preparations_fail_closed(
    c,
):
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    ctx = deepcopy(c["context"])
    section(ctx["normalized_content"], "condition")["html"] += (
        "<p>Ещё найдите приближённые корни.</p>"
    )
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    ctx = deepcopy(c["context"])
    s = section(ctx["normalized_content"], "condition")
    s["html"] = s["html"].replace(r"\pi", r"2\pi")
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    specs = list(generated(c))
    if specs:
        specs[0] = {**specs[0], "sha256": "0" * 64}
        with pytest.raises(UnsupportedCondition):
            plan(c, assets=tuple(specs))


def test_a_matching_reciprocal_exponential_reuses_the_exact_compatible_circle():
    c = case("517509")
    ctx = deepcopy(c["context"])
    s = section(ctx["normalized_content"], "condition")
    s["html"] = (
        s["html"]
        .replace(r"\log_{(4)}", r"\log_{(\frac{1}{4})}")
        .replace(r"2^{2x}", r"2^{-2x}")
    )
    a = analysis(c, ctx)
    assert a.residues == analysis(c).residues and a.selected == analysis(c).selected
    assert generated(c, ctx) == () and not any(
        t["transformation_target_id"].startswith("asset:")
        for t in plan(c, ctx).transformations
    )
    assert any(
        r"\left(\frac{1}{4}\right)^{x}" in f
        for f in formulas(plan(c, ctx).solution_html)
    )
