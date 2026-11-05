"""Verify all native named questions, independently known answers and strict source pins."""

import hashlib
from copy import deepcopy

import pytest
import sympy as sp
from midpoint_source_cases import section
from orthogonal_element_cases import BOUND, CASES, PENDING
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.orthogonal_element_geometry import (
    answer,
    frame,
    squared,
)
from solution_runner.pipelines.solids.orthogonal_element_input import read
from solution_runner.pipelines.solids.orthogonal_element_sources import (
    DATA,
    points,
    source_bytes,
)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_request_retains_every_vertex_index(case):
    assert read(section(case["context"], "condition")["html"], case["source"]) == (
        case["mode"],
        case["requested"],
    )


@pytest.mark.parametrize("case", BOUND, ids=lambda c: c["task"])
def test_named_geometry_matches_the_source_or_documented_answer_repair(case):
    expected = case.get("expected_answer")
    if expected is None:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
        node = soup.select_one("[data-inline-latex]")
        expected = node["data-inline-latex"] if node else soup.get_text(strip=True)
    else:
        assert case["correction_reason"]
    actual = answer(points(case["source"]), case["mode"], case["requested"])
    assert actual == PiParser(expected).parse().value
    assert actual == sp.sympify(case["geometry_answer"])


@pytest.mark.parametrize("case", BOUND, ids=lambda c: c["task"])
def test_unseen_rational_lengths_obey_distance_and_angle_scaling(case):
    record = DATA["figures"][case["source"]]
    factor = sp.Rational(7, 3)
    given = {k: str(factor * sp.Rational(v)) for k, v in record["given"].items()}
    original = answer(points(case["source"]), case["mode"], case["requested"])
    scaled = answer(frame(record["kind"], given), case["mode"], case["requested"])
    power = {"distance": 1, "distance_squared": 2, "angle": 0, "tangent": 0}[
        case["mode"]
    ]
    assert sp.simplify(scaled - original * factor**power) == 0


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_additional_statement_is_never_discarded(case):
    html = section(case["context"], "condition")["html"]
    with pytest.raises(ContentPlanError):
        read(html + "<p>Умножьте результат на два.</p>", case["source"])


@pytest.mark.parametrize("case", PENDING, ids=lambda c: c["task"])
def test_incomplete_old_png_cannot_use_its_stored_answer_as_a_measurement(case):
    with pytest.raises(ContentPlanError, match="PNG"):
        points(case["source"])
    assert case["source"] not in DATA["figures"]


@pytest.mark.parametrize("source", sorted(DATA["sources"]))
def test_every_numeric_condition_and_solution_image_has_exact_reviewed_bytes(source):
    raw = source_bytes(source)
    assert hashlib.sha256(raw).hexdigest() == DATA["sources"][source][1]


def test_transcription_revision_drift_cannot_silently_reuse_numbers(monkeypatch):
    source = BOUND[0]["source"]
    review = {**DATA["figures"][source], "sha256": "0" * 64}
    monkeypatch.setitem(DATA["figures"], source, review)
    with pytest.raises(ContentPlanError, match="revision"):
        points(source)


def test_missing_unmarked_base_depth_is_not_invented_for_another_request():
    review = next(
        r
        for r in DATA["figures"].values()
        if r["kind"] == "elbow" and "depth" not in r["given"]
    )
    vertices = frame(review["kind"], review["given"])
    assert "A" not in vertices
    with pytest.raises(ContentPlanError, match="measurements"):
        squared(vertices, "AE")


@pytest.mark.parametrize(
    "change", ["missing", "extra", "zero", "negative", "decimal", "overlap"]
)
def test_invalid_step_dimensions_are_rejected(change):
    given = deepcopy(DATA["figures"][BOUND[0]["source"]]["given"])
    if change == "missing":
        del given["rise"]
    elif change == "extra":
        given["guessed_length"] = "1"
    elif change == "overlap":
        given["upper_width"] = given["width"]
    else:
        given["rise"] = {"zero": "0", "negative": "-1", "decimal": "0.5"}[change]
    with pytest.raises(ContentPlanError):
        frame("step", given)


@pytest.mark.parametrize(
    "markup",
    [
        "<sub>4</sub>",
        '<sub class="x">2</sub>',
        '<var data-math-identifier="D">D</var><sub>4</sub>',
    ],
)
def test_unsupported_or_detached_vertex_indices_are_not_normalized(markup):
    with pytest.raises(ContentPlanError):
        read("<p>Найдите угол " + markup + ".</p>", None)


def test_pending_and_repaired_cases_remain_explicit():
    assert len(CASES) == 60 and len(BOUND) == 57 and len(PENDING) == 3
    assert {c["task"] for c in PENDING} == {"277871", "279871", "280371"}
    assert {c["task"] for c in BOUND if "expected_answer" in c} == {"275871", "279371"}
