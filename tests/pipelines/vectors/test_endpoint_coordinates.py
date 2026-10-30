"""Endpoint orientation, inverse displacement and auxiliary diagram compatibility."""

from copy import deepcopy
from fractions import Fraction as F
from itertools import product

import pytest
from test_coordinate_source_samples import CASES, plan

from solution_runner.pipelines.vectors.endpoints import endpoint, pair


@pytest.mark.parametrize(
    "start,delta",
    tuple(product([(F(-3), F(7)), (F(0), F(0)), (F(1, 2), F(-5, 4))], repeat=2)),
)
def test_forward_and_inverse_displacement_preserve_both_coordinates(start, delta):
    end = endpoint(start, delta, given_start=True)
    assert endpoint(end, delta, given_start=False) == start
    assert tuple(b - a for a, b in zip(start, end, strict=True)) == delta


@pytest.mark.parametrize(
    "text,expected",
    [
        ("(14,-1)", (F(14), F(-1))),
        ("(2{,}5;−3)", (F(5, 2), F(-3))),
        ("(1.5,2.5)", (F(3, 2), F(5, 2))),
    ],
)
def test_coordinate_pair_separators_are_unambiguous(text, expected):
    assert pair(text) == expected


@pytest.mark.parametrize("text", ["(1,2,3)", "(1;2;3)", "(2+3;4)", "(x;3)"])
def test_unsupported_pairs_fail_closed(text):
    with pytest.raises(ValueError):
        pair(text)


def test_a_changed_given_coordinate_cannot_reuse_the_old_numbered_diagram():
    case = next(c for c in CASES if c["task"] == "27724")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    original = condition["html"].replace("\xad", "").replace("\u202f", " ")
    condition["html"] = original.replace("(2; 4)", "(3; 4)")
    assert condition["html"] != original
    with pytest.raises(ValueError, match="diagram is incompatible"):
        plan(case, context)


def test_vector_direction_and_named_known_point_are_checked():
    case = next(c for c in CASES if c["task"] == "60957")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    original = condition["html"]
    condition["html"] = original.replace("A(12;1)", "B(12;1)")
    assert condition["html"] != original
    with pytest.raises(ValueError, match="endpoints must agree"):
        plan(case, context)


@pytest.mark.parametrize("task", ["60955", "27727", "27728", "27729"])
def test_inaccurate_source_diagrams_require_a_checksum_verified_prepared_replacement(
    task,
):
    from solution_runner.pipelines.core.group_profiles import get_group_profile
    from solution_runner.pipelines.core.handler_registry import get_handler
    from solution_runner.pipelines.core.handlers import PlanInput

    case = next(c for c in CASES if c["task"] == task)
    context = deepcopy(case["context"])
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)
    with pytest.raises(ValueError, match="must be prepared"):
        handler.plan(PlanInput(context))
    bad_ref = ({"asset_key": "image_1", "sha256": "wrong", "source_asset_id": "wrong"},)
    with pytest.raises(ValueError, match="must be prepared"):
        handler.plan(PlanInput(context, generated_solution_assets=bad_ref))
    result = plan(case, context)
    targets = {t["transformation_target_id"] for t in result.transformations}
    assert {"asset:image_1", "section:condition:1"} <= targets
    assert (
        next(
            t
            for t in result.transformations
            if t["transformation_target_id"] == "asset:image_1"
        )["operation"]
        == "rewrite"
    )


def test_corrected_drawings_encode_the_declared_displacements_at_equal_axis_scale():
    import json
    import xml.etree.ElementTree as ET
    from pathlib import Path

    folder = Path(__file__).parents[3] / "src/solution_runner/pipelines/vectors/assets"
    evidence = json.loads((folder / "endpoint_diagrams.json").read_text())
    corrected = [entry for entry in evidence.values() if "correction" in entry]
    assert len(corrected) == 3
    for entry in corrected:
        root = ET.fromstring((folder / entry["correction"]["filename"]).read_text())
        vector = root.find(".//*[@id='displacement']")
        dx = F(vector.attrib["x2"]) - F(vector.attrib["x1"])
        dy = F(vector.attrib["y1"]) - F(vector.attrib["y2"])
        a, b = entry["points"]
        assert dx / (b[0] - a[0]) == dy / (b[1] - a[1]) == 24
