"""Verify lossless bitmap reuse, complete numerical SVG preservation and helper geometry."""

import base64
from copy import deepcopy

import pytest
from lxml import etree
from orthogonal_element_cases import BOUND, model

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.orthogonal_element_sources import source_bytes
from solution_runner.pipelines.solids.orthogonal_element_svg import (
    DATA,
    SVG,
    XLINK,
    anchors,
    intersection,
    render,
)

CASES = [
    c for c in BOUND if c["source"] + ":" + c["mode"] + ":" + c["requested"] in DATA
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_helper_diagram_preserves_exact_source_art(case):
    key = case["source"] + ":" + case["mode"] + ":" + case["requested"]
    review = DATA[key]
    raw = source_bytes(case["source"])
    svg = render(case["source"], model(case))
    root = etree.fromstring(svg.encode())
    assert render(case["source"], model(case)) == svg
    if review["format"] == "png":
        images = root.findall("{" + SVG + "}image")
        assert len(images) == 1
        assert (
            base64.b64decode(
                images[0]
                .get("{" + XLINK + "}href")
                .removeprefix("data:image/png;base64,")
            )
            == raw
        )
        assert root.get("viewBox") == "0 0 " + " ".join(map(str, review["canvas"]))
    else:
        original = etree.fromstring(raw)
        root.remove(root[-1])
        for selector in review["recolor"]:
            a = next(
                n
                for n in original.iter("{" + SVG + "}line")
                if all(n.get(k) == v for k, v in selector.items())
            )
            b = next(
                n
                for n in root.iter("{" + SVG + "}line")
                if all(n.get(k) == v for k, v in selector.items())
            )
            b.set("stroke", a.get("stroke"))
        assert etree.tostring(root) == etree.tostring(original)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_each_new_blue_path_has_reviewed_named_endpoints(case):
    m = model(case)
    review = DATA[case["source"] + ":" + case["mode"] + ":" + case["requested"]]
    points = anchors(review)
    assert all(
        name in points and name in m.points
        for s in review["segments"]
        for name in s["ends"]
    )
    assert all(
        0 <= p[0] <= review["canvas"][0] and 0 <= p[1] <= review["canvas"][1]
        for p in points.values()
    )


def test_invalid_blue_triangle_is_rejected(monkeypatch):
    case = CASES[0]
    key = case["source"] + ":" + case["mode"] + ":" + case["requested"]
    review = deepcopy(DATA[key])
    review["segments"][0]["ends"] = ["A", "B"]
    monkeypatch.setitem(DATA, key, review)
    with pytest.raises(ContentPlanError, match="triangle"):
        render(case["source"], model(case))


def test_parallel_image_lines_do_not_create_a_guessed_auxiliary_point():
    with pytest.raises(ContentPlanError):
        intersection((0, 0), (1, 0), (0, 1), (1, 1))


def test_same_requested_segment_cannot_reuse_another_numeric_model():
    source_case = next(c for c in CASES if c["task"] == "274955")
    foreign = next(c for c in BOUND if c["task"] == "275367")
    with pytest.raises(ContentPlanError, match="dimensions"):
        render(source_case["source"], model(foreign))


def test_changed_source_revision_cannot_reuse_old_pixel_anchors(monkeypatch):
    case = CASES[0]
    key = case["source"] + ":" + case["mode"] + ":" + case["requested"]
    review = {**DATA[key], "sha256": "0" * 64}
    monkeypatch.setitem(DATA, key, review)
    with pytest.raises(ContentPlanError, match="review"):
        render(case["source"], model(case))
