"""Check area methods against determinants, side lengths and perpendicular feet."""

import itertools
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from area_basics_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
from bs4 import BeautifulSoup
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.general.area_sources import (
    HEIGHTS,
    SAS,
    source_bytes,
)
from solution_runner.pipelines.triangles.general.height_area_parent import selection
from solution_runner.pipelines.triangles.general.planner import CONDITION, _text
from solution_runner.pipelines.triangles.right.construction_svg import _bounds, _tag


def check_rows(html, case, ctx):
    if case["group"] == "27591":
        a, b = map(
            int,
            CONDITION.fullmatch(
                _text(section(ctx, "condition")["html"], condition=True)
            ).groups(),
        )
        p, q = sp.Matrix([a, 0]), sp.Matrix([b * sp.sqrt(3) / 2, sp.Rational(b, 2)])
        area = abs(sp.det(sp.Matrix.hstack(p, q))) / 2
        coords = None
    else:
        m = selection(ctx)[0]
        coords = m.points
        assert sp.simplify((coords["B"] - coords["A"]).norm() - m.a) == 0
        assert sp.simplify((coords["B"] - coords["C"]).norm() - m.b) == 0
        assert sp.simplify((coords["C"] - coords["H"]).norm() - m.h) == 0
        for start, foot, side in [("C", "H", "AB"), ("A", "K", "BC")]:
            assert (
                sp.simplify(
                    (coords[start] - coords[foot]).dot(
                        coords[side[1]] - coords[side[0]]
                    )
                )
                == 0
            )
        area = abs(sp.det(sp.Matrix.hstack(coords["B"], coords["C"]))) / 2
    for row in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        raw = row["data-inline-latex"]
        text = raw.replace(r"\sin 30^{\circ}", r"(\frac{1}{2})")
        if coords is None:
            text = re.sub(
                r"(?<![A-Za-z\\])ab(?![A-Za-z])", "(" + str(a * b) + ")", text
            )
            text = re.sub(r"\bS\b", lambda _: "(" + sp.latex(area) + ")", text)
        else:
            text = text.replace("S_{ABC}", "(" + sp.latex(area) + ")")
            text = re.sub(
                r"[ABCHK]{2}",
                lambda m, coords=coords: (
                    "("
                    + sp.latex(sp.simplify((coords[m[0][0]] - coords[m[0][1]]).norm()))
                    + ")"
                ),
                text,
            )
        terms = [TrigonometricParser(t).parse().value for t in text.split("=")]
        assert len(terms) > 1 and all(sp.simplify(t - terms[0]) == 0 for t in terms), (
            raw
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_methods_answers_geometry_and_empty_replay(case):
    ctx = deepcopy(case["context"])
    expected = BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text()
    for key in ("answer", "solution"):
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], case, ctx)
    assert plan(case, ctx).transformations == ()
    old, new = (
        BeautifulSoup(section(c, "condition")["html"], "html.parser")
        for c in [before, ctx]
    )
    old.img.decompose()
    new.img.decompose()
    assert str(old) == str(new)
    assert get_group_profile(case["group"]).existing_solution_policy == "rewrite"


def height_case(a, b, h):
    case = PARENTS["27623"]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    section(ctx, "condition")["html"] = (
        f"<p>{image}У треугольника со сторонами {a} и {b} проведены высоты к этим сторонам. Высота, проведенная к первой стороне, равна {h}. Чему равна высота, проведенная ко второй стороне?</p>"
    )
    return case, ctx


@pytest.mark.parametrize(
    "a,b,h",
    [
        (9, 6, 4),
        (15, 5, 1),
        (8, 4, 1),
        (56, 8, 7),
        (6, 6, 3),
        (5, 8, 4),
        (5, 3, 3),
        (5, 4, "2{,}4"),
    ],
)
def test_two_height_positions_coincident_feet_and_exact_decimals(a, b, h):
    case, ctx = height_case(a, b, h)
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], case, ctx)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_extra_facts_are_never_discarded(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += f"<p>{extra}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", list(GROUPS))
def test_unknown_parent_method_is_not_silently_accepted(group):
    with pytest.raises(ContentPlanError):
        plan(PARENTS[group], parent=parent_html(group) + "<p>Другой способ.</p>")


@pytest.mark.parametrize(
    "a,b,h,lost",
    [(9, 6, 4, False), (6, 6, 3, False), (5, 3, 3, False), (9, 6, 4, True)],
)
def test_local_frozen_roundtrip_corrected_figure_and_readback(a, b, h, lost):
    case, ctx = height_case(a, b, h)
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    rule = GROUPS["27623"]["rule"]
    kwargs = {"parent_solution_html": parent_html("27623")}
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": case["task"]},
        HEIGHTS,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, HEIGHTS, rule, **kwargs)
    assert result["status"] == ("failed" if lost else "applied"), result
    assert len(gateway.uploads) == int(not (a == b == 6))
    if not lost:
        assert (
            _apply_record(gateway, record, HEIGHTS, rule, **kwargs)["status"]
            == "already_complete"
        )


@pytest.mark.parametrize("a,b,h", [(0, 6, 4), (9, 0, 4), (9, 6, 0), (9, 6, 7)])
def test_invalid_triangle_data_are_rejected(a, b, h):
    case, ctx = height_case(a, b, h)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", list(GROUPS))
@pytest.mark.parametrize("kind", ["extra", "unknown", "url", "reference"])
def test_unreviewed_assets_fail_closed(group, kind):
    case = PARENTS[group]
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    if kind == "extra":
        ctx["normalized_content"]["assets"].append({"asset_key": "image_2"})
    elif kind == "unknown":
        asset["asset_id"] = "other"
        asset["url"] = "/assets/other"
    elif kind == "url":
        asset["url"] = "/assets/other"
    else:
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            asset["asset_id"], "other"
        )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("source", [SAS, HEIGHTS])
def test_sources_are_packaged_and_hash_pinned(source):
    assert source_bytes(source).lstrip().startswith((b"<?xml", b"<svg"))


@pytest.mark.parametrize("values", [(9, 6, 4), (5, 3, 3)])
def test_close_and_coincident_foot_labels_do_not_overlap_or_leave_canvas(values):
    _, ctx = height_case(*values)
    root = ET.fromstring(selection(ctx)[-1]["svg_text"])
    boxes = []
    for group in root.findall(_tag("g")):
        if not group.get("id", "").startswith("label-"):
            continue
        x, y, w, h = _bounds(group)
        shift = re.fullmatch(
            r"translate\(([-\d.]+) ([-\d.]+)\)", group.get("transform")
        )
        assert shift
        boxes.append((x + float(shift[1]), y + float(shift[2]), w, h))
    assert len(boxes) == 5
    vx, vy, vw, vh = map(float, root.get("viewBox").split())
    assert all(
        vx <= x and vy <= y and x + w <= vx + vw + 1e-5 and y + h <= vy + vh + 1e-5
        for x, y, w, h in boxes
    )
    for (x, y, w, h), (a, b, c, d) in itertools.combinations(boxes, 2):
        assert x + w <= a or a + c <= x or y + h <= b or b + d <= y
