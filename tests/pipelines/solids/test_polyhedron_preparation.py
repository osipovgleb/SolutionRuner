"""Verify volume proofs against independent hull volumes, areas and heights."""

import itertools
import re
from copy import deepcopy
from types import SimpleNamespace

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from polyhedron_source_cases import CASES, GROUPS, arguments, plan, read, saved_answer
from polyhedron_volume_oracle import volume
from test_distance_preparation import verify

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.solids import box_coordinates as c
from solution_runner.pipelines.solids import polyhedron_proofs as proof
from solution_runner.pipelines.solids.polyhedron_geometry import recognize


def quantities(m):
    variables = {
        proof.BOX: m.box_volume,
        proof.PYRAMID: m.answer,
        proof.SOLID: m.answer,
        proof.CORNER: m.box_volume / 6,
    }
    if m.solid.kind == "central_tetrahedron":
        return variables
    if not m.squares:
        variables.update(
            {
                proof.AREA: sp.Rational(1, 2),
                proof.FACE: sp.Integer(1),
                "h": m.box_volume,
            }
        )
        return variables
    points = {
        n: sp.Matrix([x * sp.sqrt(s) for x, s in zip(p, m.squares)])
        for n, p in c.VERTICES.items()
    }
    base = [points[n] for n in m.solid.base]
    normal = (base[1] - base[0]).cross(base[2] - base[0])
    area = sum(
        sp.sqrt(v.dot(v)) / 2
        for v in [
            (base[i] - base[0]).cross(base[i + 1] - base[0])
            for i in range(1, len(base) - 1)
        ]
    )
    top = points[m.solid.apex] if m.solid.apex else points[m.solid.upper[0]]
    height = sp.simplify(abs(normal.dot(top - base[0])) / sp.sqrt(normal.dot(normal)))
    variables.update(
        {proof.AREA: area, proof.FACE: area * (2 if len(base) == 3 else 1), "h": height}
    )
    return variables


def verify_proof(result, m):
    soup = BeautifulSoup(solution_html(result), "html.parser")
    for tag in soup.select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        for key, amount in sorted(
            quantities(m).items(), key=lambda item: -len(item[0])
        ):
            replacement = "(" + sp.latex(amount) + ")"
            if key == "h":
                formula = re.sub(
                    r"(?<![A-Za-z\\])h(?![A-Za-z])", lambda _, v=replacement: v, formula
                )
            else:
                formula = formula.replace(key, replacement)
        tag["data-inline-latex"] = formula
    dimensions = m.squares or (sp.Integer(1), sp.Integer(1), m.box_volume**2)
    verify(str(soup), SimpleNamespace(squares=dimensions))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_proof_equalities_immutable_input_and_empty_replay(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    m = read(case)
    assert (
        ctx == before
        and sp.simplify(
            ScalarParser(result.answer).parse()
            - ScalarParser(saved_answer(case)).parse()
        )
        == 0
    )
    verify_proof(result, m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    before_ids = {a["asset_id"] for a in before["normalized_content"]["assets"]}
    assert before_ids <= {a["asset_id"] for a in ctx["normalized_content"]["assets"]}
    note = BeautifulSoup(solution_html(result), "html.parser").find(
        "b", string="Примечание."
    )
    assert bool(note) == (case["group"] == "245338")


def condition(names):
    return (
        "<p>Найдите объем многогранника, вершинами которого являются точки "
        + ", ".join(names)
        + " прямоугольного параллелепипеда ABCDA_1B_1C_1D_1, у которого AB=2, AD=3, AA_1=4.</p>"
    )


SHAPES = []
for size in (4, 5, 6):
    for names in itertools.combinations(c.VERTICES, size):
        try:
            recognize(names)
        except ContentPlanError:
            continue
        SHAPES.append(names)


@pytest.mark.parametrize("names", SHAPES)
def test_every_supported_shape_prepares_actual_volume_proof_and_correct_diagrams(names):
    case = next(c for c in CASES if c["task"] == "245335")
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").find("img")
    section(ctx, "condition")["html"] = condition(names).replace(
        "<p>", "<p>" + str(image), 1
    )
    result = plan(case, ctx)
    m = read({**case, "context": ctx})
    assert m.answer == sp.Rational(
        volume([tuple(x * s for x, s in zip(c.VERTICES[n], (2, 3, 4))) for n in names])
    )
    verify_proof(result, m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["primary", "html", "assets"])
def test_parent_profile_and_method_pins(group, field):
    case = next(c for c in CASES if c["task"] == group)
    args = arguments(group)
    changes = (
        {"parent_asset_id": "foreign"}
        if field == "primary"
        else {
            "parent_solution_html": args["parent_solution_html"] + "<p>Другой метод</p>"
        }
        if field == "html"
        else {"parent_solution_assets": ({"asset_key": "image_9"},)}
    )
    with pytest.raises(ContentPlanError):
        plan(case, **changes)
    profile = get_group_profile(group)
    handler = get_handler(GROUPS[group]["rule"])
    handler.validate()
    assert profile.source_group_id == GROUPS[group]["group_uuid"]
    assert (
        handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )


def test_parent_side_face_method_keeps_the_parallel_height_direction():
    case = next(c for c in CASES if c["task"] == "245339")
    m = read(case)
    assert m.solid.axis == 1 and m.solid.foot == "B_1" and m.solid.apex == "C_1"
    assert m.solid.base == ("A", "B", "B_1")


@pytest.mark.parametrize(
    "names", [("A", "B", "C", "D"), ("A", "B", "C", "A"), ("A", "B", "C", "Z")]
)
def test_invalid_or_degenerate_solid_rejected_before_planning(names):
    case = CASES[0]
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = condition(names)
    # Remove the reviewed condition image and its metadata together.
    ctx["normalized_content"]["assets"] = []
    section(ctx, "condition")["asset_keys"] = []
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", ["27209", "245338"])
def test_known_affine_total_volume_supports_a_noncentral_triangular_pyramid(group):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").find("img")
    section(ctx, "condition")["html"] = (
        "<p>"
        + str(image)
        + "Объем параллелепипеда ABCDA_1B_1C_1D_1 равен 6. Найдите объем треугольной пирамиды ABCD_1.</p>"
    )
    result = plan(case, ctx)
    m = read({**case, "context": ctx})
    assert not m.given and m.answer == 1 and not m.squares
    verify_proof(result, m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
