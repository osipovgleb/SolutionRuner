"""Every native input and every displayed parent-style equation is checked independently."""

from copy import deepcopy

import pytest
from midpoint_projection_equations import verify
from midpoint_projection_geometry import geometry
from midpoint_projection_source_cases import CASES, read
from midpoint_source_cases import section
from projection_plane_equation_oracle import equal

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.spatial_distance_model import (
    condition_text,
    read_question,
)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_eighteen_native_model_answers_against_coordinates(case):
    m = read(case["context"])
    _, independent = geometry(m)
    assert equal(independent, m.answer)


@pytest.mark.parametrize(
    "case",
    CASES,
    ids=lambda c: c["task"],
)
def test_every_displayed_midpoint_proof_equation(case):
    m = read(case["context"])
    html = verify(m)
    if case["task"] == "507660":
        assert r"6{,}5=\frac{13}{2}" in html


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_complete_readers_are_connected_to_main_dispatch(case):
    result = read_question(section(case["context"], "condition")["html"])
    expected = read(case["context"])
    assert result == expected


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_requirements_refuse_complete_readers(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также площадь.</p>"
    with pytest.raises(ContentPlanError):
        read(ctx)


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("507611", "ADD_1", "ABC"),
        ("507611", "A_1D_1 = 6", "A_1D_1 = 0"),
        ("484559", "M — середина ребра SA. ", ""),
        ("484559", "SC = 25", "SC = 2"),
        ("511324", "равна 5", "равна 6"),
        ("485934", "BC = 8", "BC = 12"),
        ("485943", "AB = 5", "AB = 1"),
        ("525393", r"AB=AC=\sqrt{29}", "AB=AC=100"),
        (
            "526216",
            r"в отношении \frac{2}{3}, считая от вершины C",
            "в отношении 1, считая от вершины C",
        ),
    ],
)
def test_false_claims_and_impossible_solids_refuse(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        read(ctx)
