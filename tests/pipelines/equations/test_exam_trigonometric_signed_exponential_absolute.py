"""Signed absolute exponents retain empty cases, positive substitutions and circles."""

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
from solution_runner.pipelines.equations.exam_trigonometric_exponential_absolute import (
    E,
    sign_case,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition, section

CASES = json.loads(
    (
        Path(__file__).parent
        / "fixtures/category_14_trigonometric_signed_exponential_absolute.json"
    ).read_text()
)["cases"]
R = sp.Rational


def parent():
    return section(CASES[0]["context"]["normalized_content"], "solution")["html"]


def analysis(c, formula=None, prototype=None):
    _, f, i, b = read(c["context"])
    return analyze(formula or f, i, b, parent() if prototype is None else prototype)


def plan(c, context=None, prototype=None):
    handler = get_handler(get_group_profile(c["group"]).content_rule_key)
    assert handler.diagram_specs(context or c["context"]) == ()
    return handler.plan(
        PlanInput(
            context or c["context"],
            parent_solution_html=parent() if prototype is None else prototype,
        )
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_complete_and_selected_roots_satisfy_actual_signed_root_equations(c):
    a = analysis(c)
    original = c["task"] == "674931"
    assert (a.residues, a.selected) == (
        ((R(1, 3), R(5, 3)), (R(11, 3),))
        if original
        else ((R(2, 3), R(4, 3)), (-R(8, 3),))
    )
    d = a.exponential_absolute
    assert d.radical_sign == (-1 if original else 1) and d.substitution == "y"
    assert tuple(row.sign for row in d.cases) == (-1, 1)
    empty = next(row for row in d.cases if not row.polynomial.has(E))
    assert (
        empty.polynomial != 0 and empty.powers == empty.levels == empty.accepted == ()
    )
    reciprocal = next(row for row in d.cases if row.polynomial.has(E))
    assert reciprocal.accepted == ((R(1, 2),) if original else (-R(1, 2),))
    assert reciprocal.levels.count(None) == 1
    with mp.workdps(65):
        for q in [*(R(n, 48) for n in range(-216, 217)), *a.residues, *a.selected]:
            x = mp.mpf(str(sp.N(q, 70))) * mp.pi
            s, t = mp.sin(x), mp.cos(x)
            radical = mp.sqrt(max(0, 1 - s * s))
            base, sign, rhs = (
                (49, -1, -mp.mpf(48) / 7) if original else (36, 1, mp.mpf(35) / 6)
            )
            zero = abs(
                mp.power(base, sign * radical) - mp.power(base, t) - rhs
            ) < mp.mpf("1e-48")
            assert zero == (q % 2 in a.residues)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_saved_answers_unused_and_replay_preserves_conditions_assets_and_parent_order(
    c,
):
    before = deepcopy(c["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx["normalized_content"], key)["html"] = "<p>UNUSED 999</p>"
    p = plan(c, ctx)
    assert p == plan(c)
    assert (
        p.condition_html == section(before["normalized_content"], "condition")["html"]
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
    html = p.solution_html
    f = [
        n["data-inline-latex"]
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert f.index(r"(\cos x)<0") < f.index(r"(\cos x)\ge0")
    assert any(v.startswith("y=") and v.endswith(">0") for v in f)
    assert "показательная функция положительна" in html
    aid = before["normalized_content"]["assets"][0]["asset_id"]
    assert html.count('data-asset-id="' + aid + '"') == 1 and html.index(
        "<img"
    ) < html.index("Используя")
    validate(CIRCLES[aid], analysis(c))


def test_exact_catalog_binding_reuses_existing_handler():
    p = get_group_profile("674931")
    assert (
        p.source_group_id,
        p.snapshot_theme_id,
        p.theme_order_index,
        p.group_order_index,
    ) == (
        "230dd498-18b2-42bd-9a7f-a114456f3297",
        "76619b09-5e8b-45b2-baad-ae54e9eaf162",
        11,
        39,
    )
    assert p.content_rule_key == "exam-trigonometric-polynomial-circle"


def test_nonzero_constant_is_empty_but_zero_identity_is_not_a_finite_root_case():
    assert sign_case(49, (1, -1, R(48, 7)), -1, radical_sign=-1).powers == ()
    for sign in (1, -1):
        with pytest.raises(UnsupportedCondition):
            sign_case(49, (1, -1, 0), sign, radical_sign=sign)
    closed = sign_case(sp.Integer(3), (2024, -1, -2023), -1)
    strict = sign_case(sp.Integer(3), (2024, -1, -2023), -1, strict=True)
    assert closed.accepted == (0,) and strict.accepted == ()


@pytest.mark.parametrize(
    "old,new",
    [
        (r"\cos x\lt 0", r"\cos x\le 0"),
        ("y=49^{\\cos x}", "y=49^{\\sin x}"),
        (r"\frac{1}{y}", "y"),
        ("y^{2}", "y^{3}"),
    ],
)
def test_changed_parent_cases_or_substitution_method_fail_closed(old, new):
    changed = parent().replace(old, new)
    assert changed != parent()
    with pytest.raises(UnsupportedCondition):
        plan(CASES[0], prototype=changed)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_native_source_bytes_frames_markers_and_selection_are_bound(c):
    aid = c["context"]["normalized_content"]["assets"][0]["asset_id"]
    entry = CIRCLES[aid]
    svg = gzip.decompress((DIRECTORY / (aid + ".svgz")).read_bytes())
    assert hashlib.sha256(svg).hexdigest() == entry["sha256"]
    paths = {n.get("d") for n in ET.fromstring(svg).iter() if n.tag.endswith("path")}
    assert entry["native_circle_path"] in paths
    assert len(entry["green_markers"]) == 2 and entry["excluded_markers"] == []
    for p in entry["green_markers"]:
        assert p["path_d"] in paths
        frame = p["native_frame"]
        assert frame["path_d"] == entry["native_circle_path"]
        theta = float(R(p["angle"])) * math.pi
        assert (
            math.hypot(
                p["x"] - frame["cx"] - frame["rx"] * math.cos(theta),
                p["y"] - frame["cy"] + frame["ry"] * math.sin(theta),
            )
            < 3
        )
    entry = deepcopy(entry)
    entry["bounds"][0] = "0"
    with pytest.raises(UnsupportedCondition):
        validate(entry, analysis(c))
    ctx = deepcopy(c["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(c, ctx)
