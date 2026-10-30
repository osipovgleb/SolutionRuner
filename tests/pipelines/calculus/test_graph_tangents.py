"""Source graph proofs, checksum refusal and signed slope invariants."""

import hashlib
import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from solution_runner.pipelines.calculus import graph_tangents as graph
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_9_graph.json").read_text()
)
CASES = DATA["cases"]


def plan(case, context, *, downloaded=None, generated=None):
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)
    content = case["context"]["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    asset = next(
        a for a in content["assets"] if a["asset_key"] in condition["asset_keys"]
    )
    source = (graph._ASSETS / (asset["asset_id"] + ".svg")).read_bytes()
    if generated is None:
        generated = tuple(
            {
                **spec,
                "source_asset_id": "local-prepared-triangle",
                "url": "/assets/local-prepared-triangle",
            }
            for spec in handler.diagram_specs(context)
        )
    return handler.plan(
        PlanInput(
            context,
            condition_asset_bytes=source if downloaded is None else downloaded,
            generated_solution_assets=generated,
        )
    )


def _apply_local(context, transformations):
    content = context["normalized_content"]
    for t in transformations:
        if t["transformation_target_id"].startswith("asset:"):
            content["assets"].append(deepcopy(t["value"]))
            continue
        section = next(
            s
            for s in content["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        )
        section.update(t["value"])


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_source_registration_reuses_one_family(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["uuid"]
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.group_order_index == group["order"]
    assert profile.content_rule_key == "calculus-graph-tangent-slope"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["group"] + "-" + c["task"])
def test_source_answer_proof_and_assets_are_independent_and_idempotent(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    expected = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    expected = BeautifulSoup(expected, "html.parser").get_text(strip=True)
    result = plan(case, context)
    assert parse_rational(result.answer) == parse_rational(expected)
    assert original == context
    assert not any(
        t["transformation_target_id"].startswith("section:condition")
        for t in result.transformations
    )
    html = next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert len(BeautifulSoup(html, "html.parser").select("[data-inline-latex]")) == 5
    assert "180^" in html if result.answer.startswith("-") else "180^" not in html
    assert len(BeautifulSoup(html, "html.parser").find_all("img")) == 1
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999999</p>"
    assert plan(case, context).answer == result.answer
    context = deepcopy(original)
    _apply_local(context, result.transformations)
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["group"] + "-" + c["task"])
def test_changed_download_is_refused(case):
    with pytest.raises(ValueError, match="downloaded diagram"):
        plan(case, deepcopy(case["context"]), downloaded=b"<svg/>changed")


@pytest.mark.parametrize(
    "extra",
    [
        "<p>Удвойте ответ.</p>",
        "<script>doubleAnswer()</script>",
        '<span data-inline-latex="+1"></span>',
    ],
)
@pytest.mark.parametrize("leading", [True, False])
def test_unparsed_instructions_are_not_ignored(extra, leading):
    case = CASES[0]
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        extra + condition["html"] if leading else condition["html"] + extra
    )
    original = deepcopy(context)
    with pytest.raises(ValueError):
        plan(case, context)
    assert context == original


@pytest.mark.parametrize("mutation", ["attachment", "visible", "foreign"])
def test_unknown_or_mismatched_graph_is_refused(mutation):
    case = CASES[0]
    context = deepcopy(case["context"])
    content = context["normalized_content"]
    if mutation == "attachment":
        content["assets"][0]["asset_id"] = "unknown"
    elif mutation == "visible":
        content["sections"][0]["html"] = content["sections"][0]["html"].replace(
            'data-asset-id="', 'data-asset-id="unknown-'
        )
    else:
        content["assets"].append({"asset_id": "unknown", "asset_key": "foreign"})
    with pytest.raises(ValueError):
        plan(case, context)


@pytest.mark.parametrize("sx,sy", [(1, 1), (2, 3), (-2, 3), (2, -3)])
def test_signed_slope_comes_from_coordinates_and_scales_in_each_axis(sx, sy):
    entry = {
        "vertices": {"A": [2 * sx, 5 * sy], "B": [2 * sx, -sy], "C": [-2 * sx, -sy]},
        "line_points": [[-2 * sx, -sy], [2 * sx, 5 * sy]],
    }
    assert graph.model(entry)[-1] == Fraction(3 * sy, 2 * sx)
    shifted = deepcopy(entry)
    shifted["vertices"] = {
        k: [x + 7, y - 13] for k, (x, y) in entry["vertices"].items()
    }
    shifted["line_points"] = [[x + 7, y - 13] for x, y in entry["line_points"]]
    assert graph.model(shifted)[-1] == graph.model(entry)[-1]


@pytest.mark.parametrize(
    "vertices,points",
    [
        ({"A": [0, 1], "B": [0, 0], "C": [0, -1]}, [[0, 1], [0, -1]]),
        ({"A": [0, 1], "B": [0, 0], "C": [2, 0]}, [[0, 1], [2, 2]]),
        ({"A": [0, 1], "B": [0, 0], "C": [2, 0]}, [[0, 2], [2, 1]]),
        ({"A": [0, 0], "B": [0, 0], "C": [2, 0]}, [[0, 0], [2, 0]]),
    ],
)
def test_degenerate_triangle_or_incompatible_tangent_is_refused(vertices, points):
    with pytest.raises(ValueError):
        graph.model({"vertices": vertices, "line_points": points})


def test_source_assets_are_exact_reused_bytes_and_generated_triangle_keeps_source():
    for case in CASES:
        handler = get_handler(get_group_profile(case["group"]).content_rule_key)
        *_, entry, source = graph._input(case["context"])
        if entry.get("solution_asset"):
            assert handler.diagram_specs(case["context"]) == ()
            assert (
                handler.asset_requirements(case["context"])[0]["source_asset_id"]
                == entry["solution_asset"]["source_id"]
            )
        else:
            (spec,) = handler.diagram_specs(case["context"])
            assert (
                hashlib.sha256(spec["svg_text"].encode()).hexdigest() == spec["sha256"]
            )
            before, after = ET.fromstring(source), ET.fromstring(spec["svg_text"])
            assert before.attrib == after.attrib
            assert [ET.tostring(n) for n in before] == [
                ET.tostring(n) for n in list(after)[:-1]
            ]
            assert list(after)[-1].attrib["data-runner-diagram"] == "tangent_triangle"
            with pytest.raises(ValueError, match="prepared figure"):
                plan(case, case["context"], generated=())
