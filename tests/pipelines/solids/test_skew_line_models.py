"""Read all native questions and verify claims and answers with independent vectors."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import section
from projection_plane_equation_oracle import equal
from skew_line_geometry import geometry
from skew_line_source_cases import CASES, changed, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.spatial_distance_model import (
    MODES,
    condition_text,
)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_answer_and_claim_against_independent_coordinates(case):
    m = read(case)
    assert m.mode in MODES
    _, answer = geometry(m)
    assert equal(answer, m.answer)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_requirement_refuses_complete_reader(case):
    result = deepcopy(case)
    section(result["context"], "condition")["html"] += "<p>Найдите также площадь.</p>"
    with pytest.raises(ContentPlanError):
        read(result)


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("699395", "1: 3", "1: 2"),
        ("699395", "AC = 12", "AC = 18"),
        ("699395", "AA_1 = 3", "AA_1 = 0"),
        ("530402", "KM = KB", "прямая KM перпендикулярна прямой AC"),
        ("509423", "параллельно DC и AB", "параллельно DA и BC"),
        ("509423", "DC = 24", "DC = 0"),
        ("511342", "равной 1", "равной 0"),
        ("511342", r"B_1D\perp AC", r"B_1D\perp AD"),
        ("500428", "2 B_1F", "3 B_1F"),
        ("500408", "за точку C_1", "за точку B_1"),
        ("505387", r"\frac{1}{9}", "1"),
        ("505387", r"\frac{1}{9}", r"-\frac{1}{2}"),
        ("505387", "равно 6", "равно 0"),
        ("505387", ", точка N — середина ребра AC", ""),
    ],
)
def test_false_claim_and_degenerate_dimensions_fail_closed(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    with pytest.raises(ContentPlanError):
        read(changed(case, [(old, new)]))


@pytest.mark.parametrize("mutation", ("attribute", "label", "subscript"))
def test_only_the_exact_reviewed_italic_relation_is_repaired(mutation):
    case = next(c for c in CASES if c["task"] == "500428")
    soup = BeautifulSoup(section(case["context"], "condition")["html"], "html.parser")
    assert "B_1F = BB_1" in condition_text(str(soup), None)
    if mutation == "attribute":
        soup.i["class"] = "changed"
    elif mutation == "label":
        soup.i.string = "F = BC"
    else:
        soup.i.next_sibling.string = "2"
    with pytest.raises(ContentPlanError):
        condition_text(str(soup), None)
