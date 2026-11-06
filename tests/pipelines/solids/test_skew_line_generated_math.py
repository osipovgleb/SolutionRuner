"""Changed dimensions verify all parent methods, including right and obtuse cases."""

import pytest
from skew_line_equation_oracle import verify
from skew_line_source_cases import CASES, changed, read

from solution_runner.pipelines.solids.spatial_distance_proofs import render

VARIANTS = [
    (
        "699395",
        [("AB = 9", "AB = 13"), ("AC = 12", "AC = 10"), ("AA_1 = 3", "AA_1 = 5")],
    ),
    ("699395", [("AB = 9", "AB = 5"), ("AC = 12", "AC = 8"), ("AA_1 = 3", "AA_1 = 6")]),
    ("699395", [("1: 3", "2: 6")]),
    ("530402", [("AB = 8", "AB = 5"), ("AA_1 = 3", "AA_1 = 2,5")]),
    ("509423", [("DC = 24", "DC = 3"), ("AB = 10", "AB = 4")]),
    ("509423", [("DC = 24", "DC = 10")]),
    ("509423", [("DC = 24", "DC = 14,5"), ("AB = 10", "AB = 7")]),
    ("511590", [("DA = 20", "DA = 40"), ("BC = 10", "BC = 7")]),
    ("511342", [("равной 1", "равной 5")]),
    ("500112", [("D_1.", "D_1 со стороной равной 7.")]),
    ("505387", [(r"\frac{1}{9}", "0")]),
    ("505387", [(r"\frac{1}{9}", r"-\frac{1}{4}")]),
    ("505387", [("равно 6", "равно 12"), (r"\frac{1}{9}", r"\frac{3}{4}")]),
    ("511402", [(r"\frac{1}{16}", r"-\frac{1}{4}")]),
    ("505408", [(r"\frac{17}{25}", "-0,4")]),
]


@pytest.mark.parametrize("task,replacements", VARIANTS)
def test_every_changed_model_and_all_displayed_equations(task, replacements):
    case = next(c for c in CASES if c["task"] == task)
    m = read(changed(case, replacements))
    verify(render(m, {}), m)
