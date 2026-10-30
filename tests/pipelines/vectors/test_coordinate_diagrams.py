"""Exact basis recovery, angle quadrants, and verified diagram identities."""

from copy import deepcopy
from fractions import Fraction as F
from itertools import product

import pytest
from test_coordinate_source_samples import CASES, plan

from solution_runner.pipelines.vectors.coordinate_diagrams import (
    build_context_repair_plan,
    decompose,
)
from solution_runner.pipelines.vectors.coordinates import exact_angle


@pytest.mark.parametrize(
    "a,b",
    [
        ((1, 3), (2, 1)),
        ((0, 2), (3, 0)),
        ((-2, 4), (1, -3)),
        ((F(1, 2), F(-1, 3)), (F(2, 3), F(3, 4))),
    ],
)
@pytest.mark.parametrize(
    "k,l", tuple(product([F(-3), F(0), F(1, 2), F(7, 3)], repeat=2))
)
def test_basis_coefficients_reconstruct_both_components(a, b, k, l):
    a, b = tuple(map(F, a)), tuple(map(F, b))
    c = tuple(k * x + l * y for x, y in zip(a, b, strict=True))
    assert decompose(a, b, c) == (k, l)


@pytest.mark.parametrize(
    "a,b", [((0, 0), (1, 2)), ((1, 2), (2, 4)), ((3, -1), (-6, 2))]
)
def test_a_singular_basis_never_produces_a_coefficient(a, b):
    with pytest.raises(ValueError, match="noncollinear"):
        decompose(tuple(map(F, a)), tuple(map(F, b)), (F(3), F(5)))


@pytest.mark.parametrize(
    "b,expected",
    [
        ((1, 0), 0),
        ((1, 1), 45),
        ((0, 1), 90),
        ((-1, 1), 135),
        ((-1, 0), 180),
        ((-1, -1), 135),
        ((0, -1), 90),
        ((1, -1), 45),
    ],
)
def test_exact_angles_respect_the_full_zero_to_180_degree_range(b, expected):
    assert exact_angle((F(3), F(0)), tuple(map(F, b))) == expected


@pytest.mark.parametrize("a,b", [((0, 0), (1, 1)), ((1, 0), (0, 0)), ((1, 0), (2, 1))])
def test_undefined_or_nonstandard_angles_fail_closed(a, b):
    with pytest.raises(ValueError):
        exact_angle(tuple(map(F, a)), tuple(map(F, b)))


def _diagram_case():
    return next(c for c in CASES if c["task"] == "644820")


def test_missing_or_changed_downloaded_svg_cannot_be_used_for_a_plan():
    context = deepcopy(_diagram_case()["context"])
    for data in (None, b"<svg/>"):
        with pytest.raises(ValueError, match="downloaded diagram bytes"):
            build_context_repair_plan(context, condition_asset_bytes=data)


def test_an_unknown_asset_cannot_borrow_a_known_mathematical_transcription():
    case = _diagram_case()
    context = deepcopy(case["context"])
    context["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(ValueError, match="audited mathematical transcription"):
        build_context_repair_plan(context, condition_asset_bytes=b"<svg/>")


def test_visible_asset_identity_must_match_the_attached_svg():
    case = _diagram_case()
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    old = context["normalized_content"]["assets"][0]["asset_id"]
    condition["html"] = condition["html"].replace(old, "unknown")
    with pytest.raises(ValueError, match="visible diagram"):
        plan(case, context)


def test_basis_target_is_parsed_from_the_question():
    case = _diagram_case()
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    original = condition["html"]
    condition["html"] = original.replace("<i>k</i>.</p>", "<i>l</i>.</p>")
    assert condition["html"] != original
    assert plan(case, context).answer == "3"
