"""Exponential quadratics retain source methods, original domains and figures."""

import gzip
import hashlib
import json
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
from solution_runner.pipelines.equations.exam_trigonometric_power_units import (
    normalize,
)
from solution_runner.pipelines.equations.verified_expression_repair import (
    repair_verified_condition,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_power_polynomial.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
REPAIRS = {"505102", "505126", "514650", "533829", "563395", "628389"}
DIRECT = {
    "514650",
    "527978",
    "563395",
    "623352",
    "627988",
    "646294",
    "660090",
    "676259",
}


def case(task):
    return next(c for c in CASES if c["task"] == task)


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


def plan(c, ctx=None, prototype=None, assets=None):
    return get_handler(get_group_profile(c["group"]).content_rule_key).plan(
        PlanInput(
            ctx or c["context"],
            parent_solution_html=prototype or parent(c),
            generated_solution_assets=generated(c, ctx) if assets is None else assets,
        )
    )


def forms(html):
    return [
        v["data-inline-latex"]
        for v in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]


def original_value(task, x):
    s, c, p = mp.sin(x), mp.cos(x), mp.power
    if task == "527978" and abs(s + 1) < mp.mpf("1e-50"):
        return None
    if task == "563395" and abs(s) < mp.mpf("1e-50"):
        return None
    if task == "628389" and abs(c) < mp.mpf("1e-50"):
        return None
    if task == "676259" and (2 * c - 1) * (mp.sqrt(3) - 2 * s) < mp.mpf("1e-50"):
        return None
    return {
        "505102": lambda: p(9, s) + p(9, -s) - mp.mpf(10) / 3,
        "505126": lambda: p(4, s) + p(4, -s) - mp.mpf(5) / 2,
        "526674": lambda: p(9, c) + p(9, -c) - mp.mpf(10) / 3,
        "526695": lambda: p(4, c) + p(4, -c) - mp.mpf(5) / 2,
        "505236": lambda: p(mp.mpf(2) / 5, c) + p(mp.mpf(5) / 2, c) - 2,
        "620475": lambda: p(mp.mpf(4) / 9, c) + 2 * p(mp.mpf(2) / 3, c) - 3,
        "505386": lambda: p(mp.mpf(1) / 16, c) + 3 * p(mp.mpf(1) / 4, c) - 4,
        "505246": lambda: p(mp.mpf(4) / 5, s) + p(mp.mpf(5) / 4, s) - 2,
        "514650": lambda: p(2, 4 * c) + 3 * p(2, 2 * c) - 10,
        "517438": lambda: 8 * p(16, c) - 6 * p(4, c) + 1,
        "517445": lambda: 9 * p(81, c) - 28 * p(9, c) + 3,
        "517452": lambda: p(81, c) - 12 * p(9, c) + 27,
        "519809": lambda: p(2, s * s) + p(2, c * c) - 3,
        "519828": lambda: p(3, s * s) + p(3, c * c) - 4,
        "527707": lambda: p(4, mp.cos(2 * x)) - p(16, s * s) / 2 - 1,
        "527978": lambda: (p(3, c * c) + p(3, s * s) - 4) / (s + 1),
        "529297": lambda: p(256, s * c) - 18 * p(16, s * c) + 32,
        "533829": lambda: p(4, s - mp.mpf(1) / 4) - p(2, s) / (2 + mp.sqrt(2)) - 1,
        "544249": lambda: (
            p(2, -mp.cos(2 * x)) + 2 * mp.sqrt(2) - 5 * p(2, s * s - mp.mpf(3) / 4)
        ),
        "561729": lambda: p(2, 4 * s * s + 1) + p(2, 4 * c * c) - 18,
        "561770": lambda: p(3, 2 * s * s + 1) + p(3, 2 * c * c) - 12,
        "563395": lambda: (
            1 + 1 / p(3, c / s) - 4 * p(9, mp.cos(x - mp.pi / 4) / (mp.sqrt(2) * s))
        ),
        "623352": lambda: p(36, 2 * c + 1) + 16 * p(4, 2 * c - 1) - 24 * p(12, 2 * c),
        "627988": lambda: p(4, s) + p(4, mp.sin(x + mp.pi)) - mp.mpf(5) / 2,
        "628005": lambda: p(9, s) + p(9, mp.sin(x + mp.pi)) - mp.mpf(10) / 3,
        "628035": lambda: p(16, s) - mp.mpf(3) / 2 * p(4, s + 1) + 8,
        "628389": lambda: (
            9
            - 6 / p(2, s / c)
            - mp.mpf(3) / 2 * p(2, 2 * mp.cos(x - mp.pi / 4) / (mp.sqrt(2) * c))
        ),
        "646294": lambda: 6 * p(5, 2 * s) - 11 * p(30, s) + 5 * p(6, 2 * s),
        "660090": lambda: (
            3 * p(2, mp.sin(2 * x)) - 2 * p(6, mp.sin(2 * x)) - p(18, mp.sin(2 * x))
        ),
        "676259": lambda: (
            (p(25, s) + p(5, s + 1) - 6) / mp.sqrt((2 * c - 1) * (mp.sqrt(3) - 2 * s))
        ),
    }[task]()


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_follow_independent_original_equations(c):
    a = analysis(c)
    expected = DATA["expected"][c["task"]]
    full = tuple(map(R, expected["full"]))
    assert select(a.series, (0, 2, True, False))[0] == full
    assert a.selected == tuple(map(R, expected["selected"]))
    with mp.workdps(65):
        for n in range(-192, 193):
            q = R(n, 48)
            value = original_value(c["task"], mp.mpf(int(q.p)) / int(q.q) * mp.pi)
            assert (value is not None and abs(value) < mp.mpf("1e-43")) == (
                q % 2 in full
            )
    assert a.power_polynomial is not None


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_replay_preserves_original_inputs(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ["answer", "solution"]:
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 987654</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    for t in p.transformations:
        if t["transformation_target_id"].startswith("asset:"):
            assert c["task"] == "533829" and t["operation"] == "add"
            ctx["normalized_content"]["assets"].append(t["value"])
        else:
            next(
                s
                for s in ctx["normalized_content"]["sections"]
                if s["transformation_target_id"] == t["transformation_target_id"]
            ).update(t["value"])
    assert plan(c, ctx).transformations == ()
    assert (
        ctx["normalized_content"]["assets"][
            : len(before["normalized_content"]["assets"])
        ]
        == before["normalized_content"]["assets"]
    )
    assert c["context"] == before
    assert len(generated(c)) == (1 if c["task"] == "533829" else 0)
    assert (
        p.condition_html != section(before["normalized_content"], "condition")["html"]
    ) == (c["task"] in REPAIRS)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_named_and_direct_methods_follow_parent_and_adapt_child_unit(c):
    a = analysis(c)
    assert bool(a.power_polynomial.style.substitution) == (c["group"] not in DIRECT)
    assert a.selection_method == (
        "progressions"
        if c["group"] == "646294"
        else "circle"
        if c["context"]["normalized_content"]["assets"]
        else "inequalities"
    )
    html = plan(c).solution_html
    assert "квадратному уравнению" in html
    assert "логарифмическ" not in html.lower()


@pytest.mark.parametrize("task", sorted(REPAIRS))
def test_exact_transcriptions_cannot_repair_a_modified_condition(task):
    c = case(task)
    ctx = deepcopy(c["context"])
    section(ctx["normalized_content"], "condition")["html"] += " "
    assert repair_verified_condition(ctx, validate=read) == (ctx, None)


def test_source_533829_correction_removes_only_the_single_nonroot_marker():
    c = case("533829")
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    original = ET.fromstring(raw)
    fixed = ET.fromstring((DIRECTORY / e["corrected_file"]).read_bytes())
    old = [(n.tag, dict(n.attrib), (n.text or "").strip()) for n in original.iter()]
    new = [(n.tag, dict(n.attrib), (n.text or "").strip()) for n in fixed.iter()]
    bad = next(p for p in e["green_markers"] if p.get("inaccurate"))
    removed = [v for v in old if v not in new]
    assert len(removed) == 1 and removed[0][1]["d"] == bad["path_d"]
    assert [v for v in old if v not in removed] == new
    with pytest.raises(UnsupportedCondition):
        plan(c, assets=())


def test_excluded_bottom_point_keeps_both_original_red_cross_polygons():
    c = case("527978")
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    root = ET.fromstring(gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes()))
    (excluded,) = e["excluded_markers"]
    assert excluded["angle"] == "3/2"
    for part in excluded["cross_segments"]:
        assert part["tag"] == "polygon"
        assert any(dict(n.attrib) == part["attributes"] for n in root.iter())
    a = analysis(c)
    assert R(3, 2) not in select(a.series, (0, 2, True, False))[0]
    assert generated(c) == ()


def test_whole_radical_domain_allows_both_negative_factors_but_excludes_odd_pi():
    c = case("676259")
    a = analysis(c)
    assert a.power_polynomial.strict_root
    assert a.domain is not None and a.poles == ()
    assert select(a.series, (-4, 4, True, True))[0] == (-4, -2, 0, 2, 4)
    # Both factors are negative at pi/2, so their product belongs to the domain.
    assert a.domain.subs({S: 1, C: 0}) > 0
    assert "всего знаменателя" in plan(c).solution_html


def test_positive_divisor_uses_complete_homogeneous_monomials():
    for task in ["623352", "646294", "660090"]:
        a = analysis(case(task))
        d = a.power_polynomial
        assert d.unit.divisor != 1
        assert "положительный показательный множитель" in plan(case(task)).solution_html
    assert analysis(case("646294")).power_polynomial.unit.base == R(5, 6)


def test_negative_power_and_unreachable_square_levels_are_explicitly_rejected():
    a = analysis(case("544249"))
    assert a.power_polynomial.levels == (R(9, 4), R(1, 4))
    assert r"\frac{3}{2}" in " ".join(forms(plan(case("544249")).solution_html))
    for task in ["514650", "527707", "533829", "563395", "660090", "676259"]:
        a = analysis(case(task))
        assert None in a.power_polynomial.levels
        assert "неположительное значение" in plan(case(task)).solution_html


def test_radian_bounds_and_open_upper_endpoint_are_retained():
    a = analysis(case("533829"))
    assert a.bounds[:2] == (1 / (2 * sp.pi), 2 / sp.pi)
    assert a.selected == (R(1, 6),)
    a = analysis(case("660090"))
    assert a.bounds == (-R(9, 2), -R(5, 2), True, False)
    assert -R(5, 2) not in a.selected


def test_independent_prime_directions_and_unreviewed_methods_fail_closed():
    assert normalize(2**S + 3**S - 4, S) is None
    assert normalize(2**S + 4**C - 3, S) is None
    for task in ["505102", "514650"]:
        c = case(task)
        with pytest.raises(UnsupportedCondition):
            plan(
                c,
                prototype=parent(c)
                + "<p>Второй способ: применим неизвестную замену.</p>",
            )


@pytest.mark.parametrize(
    "task,expected",
    [
        ("505102", (3, R(1, 3))),
        ("514650", (-5, 2)),
        ("527978", (1, 3)),
        ("519809", (1, 2)),
        ("561729", (2, 16)),
        ("676259", (-6, 1)),
    ],
)
def test_power_root_order_follows_the_original_parent(task, expected):
    assert analysis(case(task)).power_polynomial.powers == expected


@pytest.mark.parametrize("task", ["505102", "529297", "628035"])
def test_middle_figure_remains_after_quadratic_roots_before_back_substitution(task):
    c = case(task)
    a = analysis(c)
    assert a.image_position == "after-polynomial"
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    (image,) = soup.find_all("img")
    nodes = list(soup.descendants)
    index = nodes.index(image)
    before = [
        v["data-inline-latex"]
        for v in nodes[:index]
        if getattr(v, "attrs", {}).get("data-inline-latex")
    ]
    after = [
        v["data-inline-latex"]
        for v in nodes[index + 1 :]
        if getattr(v, "attrs", {}).get("data-inline-latex")
    ]
    name = a.power_polynomial.style.substitution
    assert sum(v.startswith(name + "=") for v in before) >= 3
    assert any("sin" in v and "=" in v for v in after)


@pytest.mark.parametrize(
    "c",
    [c for c in CASES if c["context"]["normalized_content"]["assets"]],
    ids=lambda c: c["task"],
)
def test_unknown_circle_or_changed_interval_never_reuses_source_geometry(c):
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    ctx = deepcopy(c["context"])
    fixed, _ = repair_verified_condition(ctx, validate=read)
    condition = section(fixed["normalized_content"], "condition")
    soup = BeautifulSoup(condition["html"], "html.parser")
    soup.select("[data-inline-latex]")[1]["data-inline-latex"] = r"[0;10\pi]"
    condition["html"] = str(soup)
    with pytest.raises(UnsupportedCondition):
        plan(c, fixed)


def test_original_trig_poles_are_retained_before_exponential_cancellation():
    for task, pole in [("527978", S + 1), ("563395", S), ("628389", C)]:
        a = analysis(case(task))
        assert pole in a.poles
        assert r"\ne0" in " ".join(forms(plan(case(task)).solution_html))


def test_registered_bindings_keep_catalog_order_uuid_and_shared_handler():
    for task, record in DATA["groups"].items():
        profile = get_group_profile(task)
        assert profile.source_group_id == record["uuid"]
        assert profile.content_rule_key == "exam-trigonometric-polynomial-circle"
        assert profile.category_key == "14"
