"""Original equations, source methods, native circles and replay for 29 groups."""

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
from solution_runner.pipelines.equations.exam_trigonometric_compile import C
from solution_runner.pipelines.equations.exam_trigonometric_folding import (
    X,
    verify_identity,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

DATA = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_remaining_polynomials.json"
    ).read_text()
)
CASES = DATA["cases"]
R = sp.Rational
CORRECTED = {"627637", "630216", "630205", "642790"}


def case(task):
    return next(c for c in CASES if c["task"] == task)


def parent(c):
    return section(case(c["group"])["context"]["normalized_content"], "solution")[
        "html"
    ]


def analysis(c, formula=None):
    _, f, i, b = read(c["context"])
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
    sin, cos = mp.sin, mp.cos
    pi = mp.pi
    sqrt = mp.sqrt
    if task in ("507886", "507909") and abs(c) < mp.mpf("1e-50"):
        return None
    if task in ("530455", "530557") and abs(cos(2 * x)) < mp.mpf("1e-50"):
        return None
    if task == "515800" and s < mp.mpf("1e-50"):
        return None
    if task == "556546" and -s < mp.mpf("1e-50"):
        return None
    return {
        "507886": lambda: 2 * cos(pi / 2 - x) - mp.tan(x),
        "507909": lambda: 2 * cos(pi / 2 + x) - sqrt(3) * mp.tan(x),
        "500346": lambda: 4 * s**3 - 3 * cos(x - pi / 2),
        "522122": lambda: 1 - 4 * cos(x - 5 * pi / 12) ** 2 - sqrt(3) * cos(2 * x),
        "522094": lambda: (
            sqrt(2) * sin(2 * x) + 4 * cos(3 * pi / 8 + x) ** 2 - 2 - sqrt(2)
        ),
        "652135": lambda: 4 * sin(x + 7 * pi / 8) ** 2 + sqrt(2) * sin(2 * x) - 1,
        "522148": lambda: 4 * sin(x + 7 * pi / 8) ** 2 + sqrt(2) * sin(2 * x) - 1,
        "527386": lambda: sin(pi - x) - cos(pi / 2 + x) + 1,
        "529730": lambda: (
            sin(5 * x / 2) * cos(3 * x / 2)
            - sqrt(2) / 2 * sin(2 * x)
            - sin(3 * x / 2) * cos(5 * x / 2)
        ),
        "530455": lambda: sqrt(3) * mp.tan(7 * pi - 2 * x) + 1,
        "530557": lambda: sqrt(3) * mp.tan(5 * pi + 2 * x) - 3,
        "551499": lambda: cos(x + pi / 3) * cos(x - pi / 3) + mp.mpf(1) / 2,
        "563715": lambda: cos(2 * x - 3 * pi / 2) - sqrt(2) * s,
        "563717": lambda: cos(2 * x - pi / 2) - sqrt(3) * c,
        "563720": lambda: 4 * s**3 + 4 * sqrt(3) * c**2 + 3 * s - 4 * sqrt(3),
        "620215": lambda: sin(3 * x) - 4 * s * cos(2 * x),
        "625312": lambda: 2 * cos(2 * x - pi / 3) - cos(2 * x) - sqrt(6) * s,
        "627043": lambda: sin(pi / 4 - x) ** 2 - sin(pi / 4 + x) ** 2,
        "627637": lambda: (
            cos(3 * x) ** 2 + cos(4 * x) ** 2 + cos(5 * x) ** 2 - mp.mpf(3) / 2
        ),
        "630194": lambda: sin(2 * x) - 2 * s + 2 * c - 2,
        "630216": lambda: sin(2 * x) + 2 * sin(-x) + cos(-x) - 1,
        "630205": lambda: sin(2 * x) - 2 * sin(-x) - cos(-x) - 1,
        "638901": lambda: (
            sin(pi / 4 - x / 2) ** 2 - mp.mpf(1) / 2 - sin(pi / 4 + x / 2) ** 2
        ),
        "639002": lambda: 2 * c**3 + sin(3 * pi / 2 + x),
        "639110": lambda: 4 * c**3 - sin(5 * pi / 2 - x),
        "640279": lambda: (
            sqrt(3) * (cos(4 * x) + 1) - 2 * cos(2 * x) * (2 - cos(4 * x))
        ),
        "659130": lambda: (
            sqrt(2) * (1 - cos(4 * x)) - 2 * sin(2 * x) * (1 + cos(4 * x))
        ),
        "642157": lambda: cos(pi - x) ** 2 - mp.mpf(1) / 2 - cos(3 * pi / 2 + x) ** 2,
        "642332": lambda: 2 * c**3 - sqrt(3) * s**2 - 2 * c,
        "642333": lambda: 2 * s**3 - sqrt(2) * c**2 - 2 * s,
        "642409": lambda: 2 * c**3 - sqrt(3) * s**2 - c,
        "642725": lambda: 2 * s**2 * c + sqrt(3) * c**2 - sqrt(3),
        "642726": lambda: s * cos(2 * x) - sqrt(2) * c**2 + s,
        "642758": lambda: c * cos(2 * x) - sqrt(2) * s**2 - c,
        "642790": lambda: s * cos(2 * x) + s - sqrt(3) * c**2,
        "643715": lambda: s * cos(2 * x) + sqrt(2) * c**2 + s,
        "642778": lambda: s * cos(2 * x) + s - sqrt(3) * c**2,
        "643155": lambda: sin(2 * x) + sqrt(2) * s - 2 * sin(pi / 2 - x) - sqrt(2),
        "655784": lambda: sin(pi / 3 + x) - cos(pi / 6 + x) + sqrt(2) / 2,
        "681089": lambda: 2 * sin(x + pi / 3) - sqrt(6) + 2 * cos(x + pi / 6),
        "701645": lambda: 4 * sin(x - pi / 6) - 2 * sqrt(3) * cos(pi / 2 - x) - sqrt(3),
        "701651": lambda: 4 * sin(x - pi / 4) + 2 * sqrt(2) * cos(pi / 2 + x) - sqrt(2),
        "704184": lambda: (
            8 * c * sin(x + pi / 3) + sqrt(48) * s**2 - 9 * sqrt(3) + 8 * sin(2 * x)
        ),
        "704226": lambda: (
            8 * c * sin(x - pi / 3) - sqrt(48) * s**2 - sqrt(3) + 8 * sin(2 * x)
        ),
        "515800": lambda: (2 * c - sqrt(3)) / sqrt(7 * s),
        "556546": lambda: (sqrt(2) * c - 1) / sqrt(-5 * s),
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


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_local_replay_preserves_conditions_and_sources(c):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ["answer", "solution"]:
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 987654</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    for t in p.transformations:
        if t["transformation_target_id"].startswith("asset:"):
            assert c["task"] in CORRECTED and t["operation"] == "add"
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
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
    )
    assert c["context"] == before
    assert len(generated(c)) == (1 if c["task"] in CORRECTED else 0)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_source_svg_hash_native_paths_and_equation_marker_positions(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    raw = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == e["sha256"]
    paths = {n.get("d") for n in ET.fromstring(raw).iter() if n.tag.endswith("path")}
    for point in e["green_markers"]:
        assert point["path_d"] in paths
        f = point["native_frame"]
        assert f["path_d"] in paths
        q = float(R(point["angle"])) * math.pi
        distance = math.hypot(
            point["x"] - f["cx"] - f["rx"] * math.cos(q),
            point["y"] - f["cy"] + f["ry"] * math.sin(q),
        )
        assert distance > 5 if point.get("inaccurate") else distance < 5


@pytest.mark.parametrize("task", sorted(CORRECTED))
def test_native_correction_translates_only_one_marker_and_its_matching_outline(task):
    c = case(task)
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    e = CIRCLES[aid]
    original = ET.fromstring(
        gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    )
    fixed = ET.fromstring((DIRECTORY / e["corrected_file"]).read_bytes())
    old = list(original.iter())
    new = list(fixed.iter())
    assert len(old) == len(new)
    (bad,) = (p for p in e["green_markers"] if p.get("inaccurate"))
    correction = bad["corrected_marker"]
    pairs = correction["paths"]
    changed = []
    for a, b in zip(old, new, strict=True):
        assert a.tag == b.tag
        assert (
            "\n".join(v.rstrip() for v in (a.text or "").splitlines()).strip()
            == "\n".join(v.rstrip() for v in (b.text or "").splitlines()).strip()
        )
        if a.attrib != b.attrib:
            assert a.get("d") and b.get("d")
            attrs = dict(b.attrib)
            transform = attrs.pop("transform")
            assert attrs == a.attrib
            dx, dy = map(
                float, transform.removeprefix("translate(").removesuffix(")").split()
            )
            assert abs(bad["x"] + dx * e["native_scale"] - correction["x"]) < 1e-9
            assert abs(bad["y"] + dy * e["native_scale"] - correction["y"]) < 1e-9
            changed.append({"before": dict(a.attrib), "after": dict(b.attrib)})
    assert changed == pairs and len(changed) == 2
    frame = correction["native_frame"]
    angle = float(R(correction["angle"])) * math.pi
    assert abs(correction["x"] - frame["cx"] - frame["radius"] * math.cos(angle)) < 1e-9
    assert abs(correction["y"] - frame["cy"] + frame["radius"] * math.sin(angle)) < 1e-9
    with pytest.raises(UnsupportedCondition):
        plan(c, assets=())


@pytest.mark.parametrize("task", ["551499", "627043", "627637"])
def test_both_parent_methods_remain_in_their_original_sections(task):
    c = case(task)
    a = analysis(c)
    assert a.alternative is not None
    html = plan(c).solution_html
    assert html.count("Приведём другое решение пункта а)") == 1
    assert html.index("Приведём другое решение пункта а)") > html.rindex("</ol>")


def test_factorization_keeps_zero_first_and_triple_sine_note_after_selection():
    c = case("500346")
    a = analysis(c)
    assert a.sine_triple_note
    assert a.branches[0].candidates == (0,)
    assert a.branches[1].square_level and a.branches[1].candidates == (
        sp.sqrt(3) / 2,
        -sp.sqrt(3) / 2,
    )
    html = plan(c).solution_html
    assert html.index("Примечание") > html.rindex("</ol>")
    assert r"3\sin x-4\sin^3x=\sin3x" in forms(html)
    assert r"x=\frac{\pi k}{3},\quad k\in\mathbb Z" in forms(html)
    with pytest.raises(UnsupportedCondition):
        analysis(c, r"4\sin^3x=2\cos(x-\frac{\pi}{2})")


def test_eighth_pi_shift_is_folded_with_an_exact_identity_certificate():
    c = case("522148")
    a = analysis(c)
    assert a.scale == 2 and a.selected == (R(39, 8), R(41, 8), R(47, 8))
    assert sp.cancel(a.raw / (sp.sqrt(2) * C - 1)) in (-1, 1)
    verify_identity(
        4 * sp.cos(X + 3 * sp.pi / 8) ** 2 + sp.sqrt(2) * sp.sin(2 * X) - 1,
        1 - sp.sqrt(2) * sp.cos(2 * X),
    )
    with pytest.raises(UnsupportedCondition):
        verify_identity(sp.sin(X), sp.sin(X) + sp.Rational(1, 10**10))
    with pytest.raises(UnsupportedCondition):
        analysis(c, r"4\sin^2(x+\frac{7\pi}{16})+\sqrt2\sin2x=1")


def test_infinitive_instruction_is_complete_and_does_not_allow_extra_requests():
    c = case("642409")
    p = plan(c)
    assert analysis(c).selected == (-R(13, 6), -R(11, 6))
    assert (
        p.condition_html
        == section(c["context"]["normalized_content"], "condition")["html"]
    )
    for suffix in [" Удвойте ответ.", "<p>Округлите ответ.</p>"]:
        ctx = deepcopy(c["context"])
        section(ctx["normalized_content"], "condition")["html"] += suffix
        with pytest.raises(UnsupportedCondition):
            plan(c, ctx)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_unknown_circle_and_changed_interval_are_not_accepted(c):
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
    ctx = deepcopy(c["context"])
    s = section(ctx["normalized_content"], "condition")
    soup = BeautifulSoup(s["html"], "html.parser")
    soup.select("[data-inline-latex]")[1]["data-inline-latex"] = r"[0;10\pi]"
    s["html"] = str(soup)
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)


@pytest.mark.parametrize("task,entry", DATA["groups"].items())
def test_registered_catalog_binding_reuses_the_shared_runner(task, entry):
    p = get_group_profile(task)
    assert (
        p.source_group_id == entry["uuid"]
        and p.snapshot_theme_id == entry["theme_uuid"]
    )
    assert p.group_order_index == entry["order_index"]
    assert (
        p.category_key == "14"
        and p.content_rule_key == "exam-trigonometric-polynomial-circle"
    )


def test_cosine_triple_angle_note_does_not_trigger_the_sine_note_certificate():
    legacy = json.loads(
        (
            Path(__file__).parent
            / "fixtures/category_14_trigonometric_identity_notes.json"
        ).read_text()
    )["cases"]
    c = next(c for c in legacy if c["task"] == "682554")
    _, formula, interval, bounds = read(c["context"])
    prototype = section(c["context"]["normalized_content"], "solution")["html"]
    a = analyze(formula, interval, bounds, prototype)
    assert a.triple_angle is not None and a.triple_angle.note
    assert not a.sine_triple_note
