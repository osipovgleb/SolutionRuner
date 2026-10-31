"""Independent coordinate models verify the geometric identities and exact lengths."""

from copy import deepcopy
from fractions import Fraction as F
from itertools import permutations
import json
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_coordinate_source_samples import CASES, plan

from solution_runner.pipelines.vectors.geometric import _quadrilateral
from solution_runner.pipelines.vectors.rectangle_coordinates import dimensions


REPAIRS = json.loads(
    (Path(__file__).parent / "fixtures/group_27711_repairs.json").read_text()
)


@pytest.mark.parametrize("item,expected", list(zip(REPAIRS, ("6", "14", "32", "29", "18"))))
def test_group_27711_audited_diagram_repairs(item, expected):
    context = deepcopy(item)
    # Production transformation contexts supply these stable section targets.
    for section in context["normalized_content"]["sections"]:
        section["transformation_target_id"] = "section:" + section["section_id"]
    original = deepcopy(context)
    result = plan({"group": "27711"}, context)
    assert result.answer == expected
    assert context == original
    assert all(
        t["transformation_target_id"].startswith(("section:solution", "section:answer"))
        for t in result.transformations
    )
    solution = next(
        t for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert r"\overrightarrow{AB}" in solution["value"]["html"]


@pytest.mark.parametrize(
    "kind,expr",
    [
        (kind, expr)
        for kind in ("rectangle", "rhombus")
        for expr in ("AB+AD", "AB-AD", "AO+BO", "AO-BO", "AB-AC", "AO+DO", "AO-DO")
        if (kind, expr) != ("rectangle", "AB-AC")
    ],
)
@pytest.mark.parametrize("a,b", [(6, 8), (7, 24), (33, 44), (24, 18), (9, 9)])
def test_geometric_reductions_match_independent_coordinate_vector_algebra(
    kind, a, b, expr
):
    small, large = sorted((sp.Rational(a), sp.Rational(b)))
    points = (
        {
            "A": (-large / 2, 0),
            "B": (0, small / 2),
            "C": (large / 2, 0),
            "D": (0, -small / 2),
            "O": (0, 0),
        }
        if kind == "rhombus"
        else {
            "A": (0, 0),
            "B": (0, small),
            "C": (large, small),
            "D": (large, 0),
            "O": (large / 2, small / 2),
        }
    )
    left, right = expr[:2], expr[3:]
    sign = 1 if expr[2] == "+" else -1
    v = lambda name: tuple(
        sp.Rational(y - x)
        for x, y in zip(points[name[0]], points[name[1]], strict=True)
    )
    result = tuple(x + sign * y for x, y in zip(v(left), v(right), strict=True))
    expected = sp.sqrt(sum(x * x for x in result))
    actual, _ = _quadrilateral(kind, sp.Integer(a), sp.Integer(b), "length", expr)
    assert sp.simplify(actual - expected) == 0


@pytest.mark.parametrize("kind,expr", [("rectangle", "AB*AD"), ("rhombus", "AO*BO")])
def test_perpendicular_dot_products_remain_zero_for_unequal_dimensions(kind, expr):
    for a, b in [
        (sp.Rational(1, 2), sp.Rational(7, 3)),
        (sp.Integer(3), sp.Integer(100)),
    ]:
        assert _quadrilateral(kind, a, b, "dot", expr)[0] == 0


@pytest.mark.parametrize(
    "task,diagonals,expected",
    [
        ("60457", (7, 24), "12,5"),
        ("60607", (39, 80), "44,5"),
        ("60609", (33, 44), "27,5"),
        ("60657", (24, 18), "15"),
    ],
)
def test_wrong_source_answers_are_replaced_by_exact_half_diagonal_hypotenuses(
    task, diagonals, expected
):
    case = next(c for c in CASES if c["task"] == task)
    result = plan(case, deepcopy(case["context"]))
    assert result.answer == expected
    side = F(result.answer.replace(",", "."))
    assert (2 * side) ** 2 == sum(x * x for x in diagonals)
    assert any(
        t["transformation_target_id"].startswith("section:answer")
        for t in result.transformations
    )


def test_a_right_angle_position_cannot_be_guessed_without_its_figure():
    case = next(c for c in CASES if c["task"] == "654449")
    context = deepcopy(case["context"])
    content = context["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    soup = BeautifulSoup(condition["html"], "html.parser")
    soup.find("img").decompose()
    condition.update(html=str(soup), asset_keys=[])
    content["assets"] = []
    with pytest.raises(ValueError, match="roles require"):
        plan(case, context)


@pytest.mark.parametrize(
    "points",
    tuple(permutations([(F(-2), F(-3)), (F(-2), F(4)), (F(5), F(-3)), (F(5), F(4))])),
)
def test_rectangle_vertex_order_does_not_change_dimensions(points):
    assert dimensions(points) == ([F(-2), F(5)], [F(-3), F(4)])


@pytest.mark.parametrize(
    "points",
    [
        [(0, 0), (0, 1), (1, 0), (1, 0)],
        [(0, 0), (0, 1), (1, 0), (2, 2)],
        [(0, 0), (0, 0), (0, 0), (0, 0)],
    ],
)
def test_duplicate_or_incompatible_rectangle_vertices_are_not_accepted(points):
    with pytest.raises(ValueError, match="four distinct"):
        dimensions(points)
