"""Protect immutable identities shared by every grid-polygon strategy."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from solution_runner.pipelines.core.models import PreparedGridPolygon, ProblemTarget


def test_prepared_polygon_is_immutable_and_keeps_canonical_identities(
    tmp_path: Path,
) -> None:
    """Catch downstream stages mutating the frozen geometry or mixing IDs."""

    prepared = PreparedGridPolygon(
        problem_id="c78a3bf5-59db-4b78-93bb-b16a41fd903d",
        source_problem_id="246731",
        condition_asset_id="asset-1",
        condition_svg_path=tmp_path / "condition.svg",
        condition_svg_sha256="a" * 64,
        coordinates=((2, 2), (1, 7), (2, 11)),
        vertex_count=3,
        condition_was_replaced=True,
        converter_diagnostics={"consensus": "stable"},
    )

    assert prepared.problem_id == "c78a3bf5-59db-4b78-93bb-b16a41fd903d"
    assert prepared.source_problem_id == "246731"
    assert prepared.coordinates == ((2, 2), (1, 7), (2, 11))
    with pytest.raises(FrozenInstanceError):
        prepared.vertex_count = 4  # type: ignore[misc]


def test_problem_target_separates_source_and_internal_problem_ids() -> None:
    """Catch a target constructor that collapses source and internal identity."""

    target = ProblemTarget(
        problem_id="d5ef2aec-293f-4ffc-b036-720ee248f7ef",
        source_problem_id="5089",
        source_group_id="4808d0b7-aa63-4a5f-85ed-da28c8f80b18",
        group_key="27543",
        problem_order_index=7,
        asset_key="image_1",
    )

    assert target.problem_id != target.source_problem_id
    assert target.source_group_id != target.group_key
    assert target.asset_key == "image_1"
