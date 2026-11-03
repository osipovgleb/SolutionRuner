"""Validate both parent incenter methods using linear equations and coordinates."""

import itertools
import math
import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from incenter_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.general.incenter_figures import (
    BETWEEN,
    FOOT,
    OBTUSE,
    SOURCES,
    selection,
    source_bytes,
)


def _coordinate_angle(points, name):
    p, o, q = (points[n] for n in name)
    u, v = ((p[0] - o[0], p[1] - o[1]), (q[0] - o[0], q[1] - o[1]))
    cosine = sum(a * b for a, b in zip(u, v)) / (math.hypot(*u) * math.hypot(*v))
    return math.degrees(math.acos(max(-1, min(1, cosine))))


def check_rows(html, m):
    ratios = [sp.Rational(1, 3), sp.Rational(2, 3)] if m.mode == "between" else [None]
    for ratio in ratios:
        a, b, c = sp.symbols("A B C")
        equations = [a + b + c - 180]
        equations += (
            [c - m.c, a - ratio * (180 - m.c)]
            if ratio is not None
            else [a - m.values[0], b - m.values[1]]
        )
        solved = sp.solve(equations, [a, b, c])
        av, bv, cv = (solved[x] for x in [a, b, c])
        f = 180 - av - cv / 2
        values = {
            "A": av,
            "B": bv,
            "C": cv,
            "F": f,
            "OAB": av / 2,
            "OBA": bv / 2,
            "AOB": 180 - av / 2 - bv / 2,
            "ACF": cv / 2,
            "OAF": av / 2,
            "AOF": 180 - av / 2 - f,
        }
        reverse = dict(zip(m.frame + "DEFO", "ABCDEFO"))

        def angle(match, reverse=reverse, values=values):
            canonical = "".join(reverse[n] for n in match[1])
            return "(" + sp.latex(values[canonical]) + ")"

        for row in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
            raw = row["data-inline-latex"]
            text = re.sub(r"\\angle\s*([ABCDEFO]{3}|[ABCF])", angle, raw).replace(
                r"^{\circ}", ""
            )
            terms = [
                TrigonometricParser(term).parse().value for term in text.split("=")
            ]
            assert len(terms) > 1 and all(
                sp.simplify(t - terms[0]) == 0 for t in terms
            ), raw
        alpha, beta, gamma = (math.radians(float(v)) for v in [av, bv, cv])
        side_a, side_b = (
            math.sin(alpha) / math.sin(gamma),
            math.sin(beta) / math.sin(gamma),
        )
        cp = (side_b * math.cos(alpha), side_b * math.sin(alpha))
        total = side_a + side_b + 1
        points = {
            "A": (0, 0),
            "B": (1, 0),
            "C": cp,
            "O": ((side_b + cp[0]) / total, cp[1] / total),
            "F": (side_b / (side_a + side_b), 0),
        }
        actual = _coordinate_angle(points, "AOB" if m.mode == "between" else "AOF")
        assert abs(actual - float(m.answer)) < 1e-9


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_all_parent_steps_and_exact_condition_reuse(case):
    ctx = deepcopy(case["context"])
    expected = BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text()
    condition = section(ctx, "condition")["html"]
    for key in ("answer", "solution"):
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == expected
    model = selection(ctx)[0]
    replay(ctx, result.transformations)
    html = section(ctx, "solution")["html"]
    check_rows(html, model)
    if model.mode == "foot":
        assert (
            html.index("треугольнике ABC")
            < html.index("треугольнике ACF")
            < html.index("треугольнике AOF")
        )
    assert section(ctx, "condition")["html"] == condition
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx) == ()
    assert plan(case, ctx).transformations == ()


def synthetic(mode, frame, construction_first=False, source=None):
    group = "27764" if mode == "between" else "27778"
    case = PARENTS[group]
    ctx = deepcopy(case["context"])
    a, b, c = frame
    if source is not None:
        previous = ctx["normalized_content"]["assets"][0]["asset_id"]
        asset = ctx["normalized_content"]["assets"][0]
        asset["asset_id"] = source
        asset["url"] = "/assets/" + source
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            previous, source
        )
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    rays = f"{a}D и {b}E" if mode == "between" else f"{a}D, {b}E и {c}F"
    construction = f"{rays} — биссектрисы, пересекающиеся в точке O"
    givens = (
        f"угол {c} равен 58°"
        if mode == "between"
        else f"угол {a} равен 60°, угол {b} равен 53°"
    )
    facts = (
        f"{construction}. {givens}"
        if construction_first
        else f"{givens}. {construction}"
    )
    target = a + "O" + b if mode == "between" else a + "OF"
    section(ctx, "condition")["html"] = (
        f"<p>{image}В треугольнике ABC {facts}. Найдите угол {target}. Ответ дайте в градусах.</p>"
    )
    return case, ctx


@pytest.mark.parametrize("mode", ["between", "foot"])
@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
@pytest.mark.parametrize("construction_first", [False, True])
def test_two_methods_all_frames_and_fact_orders(mode, frame, construction_first):
    case, ctx = synthetic(mode, frame, construction_first)
    result = plan(case, ctx)
    assert result.answer == ("119" if mode == "between" else "63,5")
    model = selection(ctx)[0]
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_extra_facts_are_not_discarded(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += f"<p>{extra}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "mode,frame,source,lost",
    [
        ("between", "ABC", BETWEEN, False),
        ("between", "ABC", OBTUSE, False),
        ("foot", "ABC", FOOT, False),
        ("between", "CAB", OBTUSE, False),
        ("foot", "BCA", FOOT, False),
        ("foot", "BCA", FOOT, True),
    ],
)
def test_local_frozen_roundtrip_preserves_source_style_and_checks_readback(
    mode, frame, source, lost
):
    case, ctx = synthetic(mode, frame, source=source)
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    rule = GROUPS[case["group"]]["rule"]
    kwargs = {"parent_solution_html": parent_html(case["group"])}
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": case["task"]},
        SOURCES[mode],
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, SOURCES[mode], rule, **kwargs)
    assert result["status"] == ("failed" if lost else "applied"), result
    assert len(gateway.uploads) == int(frame != "ABC")
    if not lost:
        assert (
            _apply_record(gateway, record, SOURCES[mode], rule, **kwargs)["status"]
            == "already_complete"
        )


@pytest.mark.parametrize("group", list(GROUPS))
def test_parent_method_and_binding_are_pinned(group):
    with pytest.raises(ContentPlanError):
        plan(PARENTS[group], parent=parent_html(group) + "<p>Другой способ.</p>")
    profile = get_group_profile(group)
    handler = get_handler(profile.content_rule_key)
    assert profile.existing_solution_policy == "rewrite"
    assert handler.requires_frozen_manifest and handler.verify_content_readback


@pytest.mark.parametrize(
    "old,new",
    [
        ("AD и BE", "AD и AE"),
        ("AD и BE", "AD и BD"),
        ("биссектрисы", "высоты"),
        ("точке O", "точке F"),
        ("угол C равен", "угол A равен"),
        ("58°", "180°"),
        ("58°", "0°"),
        ("угол AOB", "угол AOF"),
    ],
)
def test_inconsistent_bisector_roles_and_angle_data_fail_closed(old, new):
    case, ctx = synthetic("between", "ABC")
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        old, new
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("mode", ["between", "foot"])
@pytest.mark.parametrize(
    "kind", ["extra", "unknown", "url", "reference", "wrong_family"]
)
def test_unreviewed_or_inconsistent_assets_fail_closed(mode, kind):
    case, ctx = synthetic(mode, "ABC")
    asset = ctx["normalized_content"]["assets"][0]
    if kind == "extra":
        ctx["normalized_content"]["assets"].append({"asset_key": "image_2"})
    elif kind == "unknown":
        asset["asset_id"] = "other"
        asset["url"] = "/assets/other"
    elif kind == "url":
        asset["url"] = "/assets/other"
    elif kind == "wrong_family":
        old = asset["asset_id"]
        new = FOOT if mode == "between" else BETWEEN
        asset["asset_id"] = new
        asset["url"] = "/assets/" + new
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            old, new
        )
    else:
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            asset["asset_id"], "other"
        )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("source", [BETWEEN, OBTUSE, FOOT])
def test_reviewed_sources_are_packaged_and_hash_pinned(source):
    assert source_bytes(source).lstrip().startswith((b"<?xml", b"<svg"))


def test_invalid_sum_of_two_given_angles_is_rejected():
    case, ctx = synthetic("foot", "ABC")
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        "53°", "120°"
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
