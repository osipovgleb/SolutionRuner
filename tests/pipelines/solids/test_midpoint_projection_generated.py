"""Changed dimensions verify the parent methods, including exterior projection feet."""

import pytest
from midpoint_projection_equations import verify
from midpoint_projection_source_cases import CASES
from midpoint_source_cases import section

from solution_runner.pipelines.solids.spatial_distance_model import (
    condition_text,
    read_question,
)

VARIANTS = [
    ("507611", [("AA_1 = 4", "AA_1 = 7"), ("C_1D_1 = 6", "C_1D_1 = 3")]),
    ("507611", [("A_1D_1 = 6", r"A_1D_1 = \sqrt{7}")]),
    ("507615", [("AB = 4", "AB = 10"), ("CC_1 = 4", "CC_1 = 2,5")]),
    ("507615", [("BC = 6", r"BC = \sqrt{5}")]),
    ("484559", [(r"7\sqrt{3}", r"3\sqrt{3}"), ("SC = 25", "SC = 5")]),
    ("484559", [(r"7\sqrt{3}", r"4\sqrt{3}"), ("SC = 25", "SC = 13")]),
    ("484559", [(r"7\sqrt{3}", r"\sqrt{3}"), ("SC = 25", "SC = 2")]),
    ("485934", [("BC = 8", "BC = 6"), ("равна 3", "равна 4")]),
    ("485934", [("AC = 5", "AC = 13"), ("BC = 8", "BC = 10"), ("равна 3", "равна 7")]),
    ("511324", [("AC=13", "AC=5"), ("BC=24", "BC=6"), ("равна 5", "равна 4")]),
    (
        "485943",
        [
            ("AB = 5", "AB = 13"),
            (r"BC=\sqrt{5}", "BC=5"),
            (r"равна \sqrt{3}", "равна 12"),
        ],
    ),
    (
        "485943",
        [
            ("AB = 5", "AB = 17"),
            (r"BC=\sqrt{5}", "BC=8"),
            (r"равна \sqrt{3}", "равна 15"),
        ],
    ),
    ("525393", [(r"\sqrt{17}", "5"), (r"\sqrt{29}", "7"), (r"2\sqrt{5}", "6")]),
    ("525393", [(r"\sqrt{17}", "5"), (r"\sqrt{29}", "5"), (r"2\sqrt{5}", "6")]),
    ("525393", [(r"\sqrt{17}", "5"), (r"\sqrt{29}", "8"), (r"2\sqrt{5}", "6")]),
    (
        "525393",
        [(r"\sqrt{17}", "5"), (r"\sqrt{29}", r"\sqrt{61}"), (r"2\sqrt{5}", "6")],
    ),
    ("526216", [(r"\frac{2}{3}", r"\frac{1}{4}")]),
    ("526216", [(r"\frac{2}{3}", "1")]),
    ("526216", [(r"\frac{2}{3}", "3")]),
    ("526216", [("SC=5", r"SC=\sqrt{13}")]),
    ("526216", [("SC=5", r"SC=3\sqrt{2}")]),
]


@pytest.mark.parametrize("task,replacements", VARIANTS)
def test_changed_dimensions_check_every_equation_and_independent_answer(
    task, replacements
):
    case = next(c for c in CASES if c["task"] == task)
    raw = condition_text(section(case["context"], "condition")["html"], None)
    for old, new in replacements:
        assert old in raw
        raw = raw.replace(old, new)
    verify(read_question("<p>" + raw + "</p>"))
