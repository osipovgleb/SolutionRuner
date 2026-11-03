"""Check both methods against actual altitude lines and all relevant point topologies."""

import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from altitude_lines_cases import CASES, parent_html, plan, section
from bs4 import BeautifulSoup
from test_altitude_quad_preparation import angle
from test_orthocenter_preparation import coordinates
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.general.orthocenter_figures import (
    LINES_SOURCE,
    SOURCE,
    selection,
    source_bytes,
)
from solution_runner.pipelines.triangles.general.orthocenter_model import LINES_RULE


def synthetic(a=58, b=72, latex=False):
    case = CASES[0]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    values = [
        f'<span data-inline-latex="{v}^{{\\circ}}"></span>' if latex else f"{v}°"
        for v in [a, b]
    ]
    section(ctx, "condition")["html"] = (
        f"<p>{image}Два угла треугольника равны {values[0]} и {values[1]}. Найдите тупой угол, который образуют высоты треугольника, выходящие из вершин этих углов. Ответ дайте в градусах.</p>"
    )
    return case, ctx


def actual_values(model):
    points = coordinates(model.alpha, model.beta)
    u = tuple(points["D"][i] - points["A"][i] for i in [0, 1])
    v = tuple(points["E"][i] - points["B"][i] for i in [0, 1])
    cosine = abs(sum(x * y for x, y in zip(u, v)) / (math.hypot(*u) * math.hypot(*v)))
    acute = math.degrees(math.acos(min(1, cosine)))
    obtuse = 180 - acute
    assert abs(obtuse - float(model.answer)) < 1e-8 and obtuse > 90
    return points, obtuse


def check_methods(html, model):
    points, obtuse = actual_values(model)
    soup = BeautifulSoup(html, "html.parser")
    methods = soup.select("section[data-content-kind=solution]")
    assert [m["data-solution-title"] for m in methods] == [
        "Решение",
        "Приведём другое решение",
    ]
    count = 9 if max(model.alpha, model.beta, model.gamma) >= 90 else 7
    assert [len(m.select("center [data-inline-latex]")) for m in methods] == [count, 6]

    def measured(name):
        vertices = {"A": "BAC", "B": "ABC", "C": "ACB"}
        return angle(points, vertices.get(name, name))

    for row in soup.select("center [data-inline-latex]"):
        expression = re.sub(
            r"\\angle\s*([ABCDEO]{3}|[ABC])",
            lambda m: "(" + str(round(measured(m[1]), 8)) + ")",
            row["data-inline-latex"],
        )
        expression = (
            expression.replace(r"\theta", "(" + str(round(obtuse, 8)) + ")")
            .replace(r"\varphi", "(" + str(float(model.alpha + model.beta)) + ")")
            .replace(r"^{\circ}", "")
        )
        sides = [TrigonometricParser(s).parse().value for s in expression.split("=")]
        assert len(sides) > 1 and all(abs(float(s - sides[0])) < 1e-7 for s in sides), (
            expression
        )
    if model.alpha > 90 or model.beta > 90:
        assert "самопересекается" in methods[0].get_text()
    assert "соответственно перпендикулярны" in methods[1].get_text()


def check_svg(diagram, model):
    root = ET.fromstring(diagram["svg_text"])
    elements = {e.get("id"): e for e in root if e.get("id")}
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    assert len(ids) == len(set(ids))

    def ends(name):
        item = elements[name]
        return [
            tuple(float(item.get(axis + str(i))) for axis in ["x", "y"]) for i in [1, 2]
        ]

    a, b = ends("AB")
    c, _ = ends("CA")
    _, d = ends("AD")
    _, e = ends("BE")
    points = dict(zip("ABCDE", [a, b, c, d, e]))
    assert abs(angle(points, "BAC") - float(model.alpha)) < 1e-3
    assert abs(angle(points, "ABC") - float(model.beta)) < 1e-3
    for origin, foot, side in [("A", "D", "BC"), ("B", "E", "CA")]:
        u = tuple(points[origin][i] - points[foot][i] for i in [0, 1])
        v = tuple(points[side[0]][i] - points[side[1]][i] for i in [0, 1])
        assert (
            abs(sum(x * y for x, y in zip(u, v)) / (math.hypot(*u) * math.hypot(*v)))
            < 1e-5
        )
    assert "CF" not in elements and "label-F" not in elements
    assert (
        elements["AD"].get("stroke") == "#007EA5"
        and elements["BE"].get("stroke") == "#143B8F"
    )
    assert {"right-D", "right-E", *("label-" + n for n in "ABCDEO")} <= elements.keys()
    if model.alpha == 90:
        assert math.dist(a, e) < 1e-5
        assert len([n for n in ids if n.startswith("merged-A-")]) == 4
    if model.beta == 90:
        assert math.dist(b, d) < 1e-5
        assert len([n for n in ids if n.startswith("merged-B-")]) == 4


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_preserve_two_methods_and_correct_crossed_figures(case):
    ctx = deepcopy(case["context"])
    condition = deepcopy(section(ctx, "condition"))
    expected = BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text()
    for key in ["answer", "solution"]:
        section(ctx, key)["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    model, *_, diagram = selection(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == expected
    if diagram:
        check_svg(diagram, model)
    replay(ctx, result.transformations)
    check_methods(section(ctx, "solution")["html"], model)
    if not diagram:
        assert section(ctx, "condition") == condition
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "a,b",
    [
        (58, 72),
        (33, 105),
        (103, 48),
        (20, 30),
        (90, 30),
        (30, 90),
        (120, 20),
        (20, 120),
    ],
)
@pytest.mark.parametrize("latex", [False, True])
def test_convex_crossed_and_right_vertex_configurations_in_both_degree_formats(
    a, b, latex
):
    case, ctx = synthetic(a, b, latex)
    model, *_, diagram = selection(ctx)
    result = plan(case, ctx)
    assert result.answer == str(max(a + b, 180 - a - b))
    if diagram:
        check_svg(diagram, model)
    replay(ctx, result.transformations)
    check_methods(section(ctx, "solution")["html"], model)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("extra", ["Удвойте ответ.", "AB=7.", "Найдите периметр."])
def test_extra_facts_are_never_discarded(case, extra):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += f"<p>{extra}</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "a,b", [(0, 72), (58, 0), (100, 80), (100, 90), (20, 70), (45, 45)]
)
def test_invalid_triangles_or_no_obtuse_angle_fail_closed(a, b):
    case, ctx = synthetic(a, b)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "old,new",
    [
        ("тупой угол", "острый угол"),
        ("Два угла", "Три угла"),
        ("из вершин этих углов", "из других вершин"),
        ("высоты треугольника", "биссектрисы треугольника"),
    ],
)
def test_changed_quantities_or_request_are_rejected(old, new):
    case, ctx = synthetic()
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        old, new
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "a,b,lost",
    [
        (58, 72, False),
        (33, 105, False),
        (103, 48, False),
        (20, 30, False),
        (90, 30, False),
        (30, 90, False),
        (33, 105, True),
    ],
)
def test_local_frozen_roundtrip_checks_two_methods_and_authoritative_condition_readback(
    a, b, lost
):
    case, ctx = synthetic(a, b)
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    kwargs = {"parent_solution_html": parent_html("27763")}
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": case["task"]},
        LINES_SOURCE,
        LINES_RULE,
        **kwargs,
    )
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, LINES_SOURCE, LINES_RULE, **kwargs)
    assert result["status"] == ("failed" if lost else "applied"), result
    assert len(gateway.uploads) == int(max(a, b, 180 - a - b) >= 90)
    if not lost:
        assert (
            _apply_record(gateway, record, LINES_SOURCE, LINES_RULE, **kwargs)["status"]
            == "already_complete"
        )


def test_missing_second_parent_method_is_rejected():
    html = parent_html("27763")
    soup = BeautifulSoup(html, "html.parser")
    soup.select("section")[1].decompose()
    with pytest.raises(ContentPlanError):
        plan(CASES[0], parent=str(soup))


@pytest.mark.parametrize("change", ["extra", "source", "reference", "url"])
def test_unreviewed_figures_or_wrong_height_family_are_rejected(change):
    case, ctx = synthetic()
    asset = ctx["normalized_content"]["assets"][0]
    if change == "extra":
        ctx["normalized_content"]["assets"].append(deepcopy(asset))
    elif change == "source":
        asset["asset_id"] = SOURCE
        asset["url"] = "/assets/" + SOURCE
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            LINES_SOURCE, SOURCE
        )
    elif change == "reference":
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            LINES_SOURCE, "unknown"
        )
    else:
        asset["url"] = "/assets/unknown"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "a,b",
    [
        ("90{,}000000000000000001", 30),
        (30, "90{,}000000000000000001"),
        ("0{,}000000000000000001", 120),
    ],
)
def test_unrepresentable_generated_geometry_fails_closed(a, b):
    case, ctx = synthetic(a, b)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "a,b,expected", [("33{,}5", 105, "138,5"), ("20{,}5", 30, "129,5")]
)
def test_exact_half_degrees_and_the_third_obtuse_angle(a, b, expected):
    case, ctx = synthetic(a, b)
    model = selection(ctx)[0]
    result = plan(case, ctx)
    assert result.answer == expected
    replay(ctx, result.transformations)
    check_methods(section(ctx, "solution")["html"], model)


def test_line_angle_is_independent_of_order_of_given_angles():
    answers = []
    for a, b in [(33, 105), (105, 33)]:
        case, ctx = synthetic(a, b)
        model = selection(ctx)[0]
        result = plan(case, ctx)
        answers.append(result.answer)
        replay(ctx, result.transformations)
        check_methods(section(ctx, "solution")["html"], model)
    assert answers == ["138", "138"]


def test_two_height_source_is_packaged_and_hash_pinned():
    assert source_bytes(LINES_SOURCE).lstrip().startswith((b"<?xml", b"<svg"))
