"""Both square-root questions use exact marked points and preserve source figures."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from test_profile_hyperbolas import plan, replay

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.numbers import parse_rational
from solution_runner.pipelines.function_graphs import root_graph

ROOT = Path(__file__).resolve().parents[3]
DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_12_roots.json").read_text()
)
CASES = DATA["cases"]


def change(case, edit):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = edit(condition["html"])
    return context


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_profiles_share_the_root_rule(group):
    p = get_group_profile(group["key"])
    assert p.content_rule_key == "square-root-function-graph"
    assert (
        p.source_group_id == group["uuid"]
        and p.snapshot_theme_id == group["theme_uuid"]
    )
    assert p.group_order_index == group["order"] and p.theme_order_index == 3
    assert (
        p.category_key == "12"
        and p.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_source_computes_from_condition_without_saved_answer_or_solution(case):
    context = deepcopy(case["context"])
    old = deepcopy(context)
    data = (ROOT / case["condition_file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == case["condition_sha256"]
    result = plan(case, context)
    saved = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "answer"
    )
    assert parse_rational(result.answer) == parse_rational(
        BeautifulSoup(saved["html"], "html.parser").get_text()
    )
    assert context == old
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>999999999</p>"
    changed = plan(case, context)
    assert changed.answer == result.answer
    assert next(
        t["value"]
        for t in changed.transformations
        if t["transformation_target_id"] == "section:solution:1"
    ) == next(
        t["value"]
        for t in result.transformations
        if t["transformation_target_id"] == "section:solution:1"
    )
    updated = replay(old, result.transformations)
    assert plan(case, updated).transformations == ()
    assert (
        updated["normalized_content"]["assets"] == old["normalized_content"]["assets"]
    )
    assert next(
        s for s in updated["normalized_content"]["sections"] if s["key"] == "condition"
    ) == next(
        s for s in old["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assert all(
        t["transformation_target_id"] != "section:condition:1"
        for t in result.transformations
    )
    html = next(
        s["html"]
        for s in updated["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.select('section[data-content-kind="solution"]')) == 1
    assert not soup.select("img")
    forms = [m["data-inline-latex"] for m in soup.select("[data-inline-latex]")]
    assert len(forms) >= 6 and forms[0].startswith("f(")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "edit",
    [
        lambda s: "<p>Дополнительное условие</p>" + s,
        lambda s: s + '<span data-inline-latex="x=2"></span>',
        lambda s: s + '<img src="other.svg"/>',
        lambda s: s.replace(r"k\sqrt{x}", r"k\sqrt{x}+1"),
        lambda s: s.replace("Най", "Определи", 1),
        lambda s: s.replace('data-asset-key="image_1"', 'data-asset-key="image_2"'),
    ],
)
def test_entire_condition_and_canonical_image_are_required(case, edit):
    with pytest.raises(ContentPlanError):
        plan(case, change(case, edit))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "mime,data",
    [("image/png", None), ("image/svg+xml", b"<svg/>"), ("image/svg+xml", b"")],
)
def test_uninspected_bytes_and_wrong_mime_fail_closed(case, mime, data):
    with pytest.raises(ContentPlanError):
        plan(case, data=data, mime=mime)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_foreign_solution_figure_is_rejected(case):
    context = deepcopy(case["context"])
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "solution"
    )["html"] = '<p><img src="extra.svg"/></p>'
    with pytest.raises(ContentPlanError):
        plan(case, context)


@pytest.mark.parametrize(
    "mode,target,point,expected",
    [
        ("value", "0", (4, 5), "0"),
        ("value", "32", (8, 4), "8"),
        ("value", "12.5", (2, -2), "-5"),
        ("argument", "0", (2, -2), "0"),
        ("argument", "7", (8, 4), "24.5"),
        ("argument", "-8", (2, -2), "32"),
    ],
)
def test_exact_radicals_and_zero_boundary(mode, target, point, expected):
    source = next(
        c
        for c in CASES
        if root_graph.marked_point(
            (ROOT / c["condition_file"]).read_bytes(), "image/svg+xml"
        )
        == point
        and root_graph.parse(c["context"])[0] == mode
    )
    forms, _ = root_graph.read(source["context"])
    raw = "f(" + target + ")" if mode == "value" else "f(x)=" + target
    context = change(source, lambda s: s.replace(forms[1], raw))
    assert parse_rational(plan(source, context).answer) == parse_rational(expected)


@pytest.mark.parametrize(
    "group,target", [("509113", "-1"), ("509113", "2"), ("509118", "-1")]
)
def test_undefined_irrational_answer_or_wrong_sign_fails(group, target):
    source = next(c for c in CASES if c["task"] == group)
    forms, _ = root_graph.read(source["context"])
    raw = "f(" + target + ")" if group == "509113" else "f(x)=" + target
    with pytest.raises(ContentPlanError):
        plan(source, change(source, lambda s: s.replace(forms[1], raw)))


def test_negative_root_coefficient_does_not_admit_positive_output():
    source = next(c for c in CASES if c["task"] == "509121")
    with pytest.raises(ContentPlanError):
        plan(source, change(source, lambda s: s.replace("f(x)=-8", "f(x)=8")))


def test_irrational_coefficient_argument_preserves_parent_squaring_method():
    source = next(c for c in CASES if c["task"] == "509120")
    result = plan(source)
    html = next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"] == "section:solution:1"
    )
    soup = BeautifulSoup(html, "html.parser")
    forms = [m["data-inline-latex"] for m in soup.select("[data-inline-latex]")]
    assert "Возведём их в квадрат" in soup.get_text()
    assert "2x=(7)^2=49" in forms
    assert r"x=\frac{49}{2}=24{,}5" in forms
    assert any(r"\sqrt{2}" in f for f in forms)


@pytest.mark.parametrize(
    "problem",
    ["color", "missing", "duplicate", "off_grid", "off_curve", "negative_x", "units"],
)
def test_registered_graph_still_requires_actual_unambiguous_curve_markers(
    problem, tmp_path, monkeypatch
):
    from xml.etree import ElementTree as ET

    from solution_runner.pipelines.function_graphs.linear_svg import NS, frame

    source = CASES[0]
    svg = ET.fromstring((ROOT / source["condition_file"]).read_bytes())
    xmap, ymap, _, _ = frame(svg)
    markers = list(svg.iter(NS + "circle"))
    nonzero = next(
        m for m in markers if float(m.get("cx")) != next(px for px, x in xmap if x == 0)
    )
    if problem == "color":
        nonzero.set("fill", "#FF0000")
    elif problem == "missing":
        svg.remove(nonzero)
    elif problem == "duplicate":
        nonzero.set("cx", str(next(px for px, x in xmap if x == 0)))
        nonzero.set("cy", str(next(py for py, y in ymap if y == 0)))
    elif problem == "off_grid":
        nonzero.set("cx", str(float(nonzero.get("cx")) + 8))
    elif problem == "off_curve":
        nonzero.set("cy", str(next(py for py, y in ymap if y == 2)))
    elif problem == "negative_x":
        nonzero.set("cx", str(next(px for px, x in xmap if x == -1)))
    data = ET.tostring(svg)
    (tmp_path / "source-evidence.json").write_text(
        json.dumps(
            {
                hashlib.sha256(data).hexdigest(): {
                    "grid_unit": [2, 1] if problem == "units" else [1, 1]
                }
            }
        )
    )
    monkeypatch.setattr(root_graph, "ASSET_DIR", tmp_path)
    with pytest.raises(ContentPlanError):
        plan(source, data=data)
