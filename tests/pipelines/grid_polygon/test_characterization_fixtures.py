"""Validate durable canary fixtures for reusable grid-polygon strategies."""

from __future__ import annotations

import json
from pathlib import Path


FIXTURE_DIR = Path(__file__).with_name("fixtures")
EXPECTED_FIXTURES = {
    "base_height_triangle.json": ("base-height-triangle", 3),
    "right_triangle.json": ("right-triangle", 3),
    "bounding_rectangle_triangle.json": ("bounding-rectangle-triangle", 3),
    "parallel_bases_trapezoid.json": ("parallel-bases-trapezoid", 4),
    "bounding_rectangle_trapezoid.json": ("bounding-rectangle-trapezoid", 4),
}


def _load_fixture(name: str) -> dict[str, object]:
    """Load one minimized characterization fixture by filename."""

    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_characterization_fixtures_cover_every_active_strategy() -> None:
    """Catch a strategy port that lacks a hand-audited parity fixture."""

    assert {path.name for path in FIXTURE_DIR.glob("*.json")} == set(
        EXPECTED_FIXTURES
    )

    fixtures = [_load_fixture(name) for name in EXPECTED_FIXTURES]
    assert {fixture["strategy_key"] for fixture in fixtures} == {
        expected[0] for expected in EXPECTED_FIXTURES.values()
    }
    assert all(fixture["schema_version"] == 1 for fixture in fixtures)


def test_characterization_fixtures_have_valid_shape_and_no_transport_data() -> None:
    """Catch malformed canaries or accidental persistence of transport secrets."""

    source_problem_ids: set[str] = set()
    forbidden_keys = {
        "api_key",
        "authorization",
        "signed_url",
        "upload_url",
        "user_id",
        "mcp_response",
    }

    for name, (strategy_key, vertex_count) in EXPECTED_FIXTURES.items():
        fixture = _load_fixture(name)
        coordinates = fixture["coordinates"]
        expected = fixture["expected"]

        assert fixture["strategy_key"] == strategy_key
        assert len(coordinates) == vertex_count
        assert all(
            isinstance(point, list)
            and len(point) == 2
            and all(isinstance(value, int) for value in point)
            for point in coordinates
        )
        assert isinstance(fixture["source_problem_id"], str)
        assert fixture["source_problem_id"] not in source_problem_ids
        source_problem_ids.add(fixture["source_problem_id"])
        assert isinstance(expected["area"], str) and expected["area"]
        assert isinstance(expected["answer_html"], str) and expected["answer_html"]
        assert expected["formula_fragments"]
        assert forbidden_keys.isdisjoint(fixture)
        assert forbidden_keys.isdisjoint(expected)
