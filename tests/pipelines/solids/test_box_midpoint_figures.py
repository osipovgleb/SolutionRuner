"""Verify exact source roles and geometry-preserving spatial label permutations."""

import hashlib
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from box_midpoint_source_cases import CASES, generated, plan, read
from midpoint_source_cases import section
from test_box_midpoint_preparation import CONFIGURATIONS, condition

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids import box_coordinates as c
from solution_runner.pipelines.solids.box_midpoint_sources import SOURCES, source_bytes
from solution_runner.pipelines.solids.box_midpoint_svg import (
    CONDITION,
    GLYPHS,
    SOLUTION,
    figure_svg,
    mapping,
)
from solution_runner.pipelines.triangles.right.construction_svg import _tag


@pytest.mark.parametrize("source", SOURCES)
def test_source_sha_remains_exact(source):
    assert hashlib.sha256(source_bytes(source)).hexdigest() == SOURCES[source][1]


@pytest.mark.parametrize("source", [CONDITION, SOLUTION])
@pytest.mark.parametrize("configuration", CONFIGURATIONS)
def test_relabelled_scene_is_an_actual_box_symmetry_with_exact_geometry_and_vector_glyphs(
    configuration, source
):
    case = CASES[-1]
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = condition(*configuration)
    m = read({**case, "context": ctx})
    names = mapping(m, source)
    origin = sp.Matrix(c.VERTICES[names["A"]])
    basis = sp.Matrix.hstack(
        *(sp.Matrix(c.VERTICES[names[n]]) - origin for n in ("B", "D", "A_1"))
    )
    assert abs(basis.det()) == 1 and basis.T * basis == sp.eye(3)
    for old, new in names.items():
        if old in c.VERTICES:
            assert origin + basis * sp.Matrix(c.VERTICES[old]) == sp.Matrix(
                c.VERTICES[new]
            )
    old_k = (
        (1, 0, sp.Rational(1, 2)) if source == SOLUTION else (1, 1, sp.Rational(1, 2))
    )
    assert tuple(origin + basis * sp.Matrix(old_k)) == dict(m.extra_points)["K"]
    if source == SOLUTION:
        assert (
            tuple(origin + basis * sp.Matrix((1, 1, sp.Rational(1, 2))))
            == dict(m.extra_points)["K_1"]
        )
    original = ET.fromstring(source_bytes(source))
    root = ET.fromstring(figure_svg(m, source))
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    library = dict(zip(GLYPHS[source], groups))
    for name in GLYPHS[source]:
        node = root.find(".//*[@id='label-" + name + "']")
        assert node is not None
        assert [p.get("d") for p in node.iter(_tag("path"))] == [
            p.get("d") for p in library[name].iter(_tag("path"))
        ]

    def geometry(r):
        return [
            ET.tostring(n)
            for n in r
            if not (n.tag == _tag("g") and list(n.iter(_tag("path"))))
        ]

    assert geometry(root) == geometry(original)


@pytest.mark.parametrize("case", CASES[:3], ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "field", ["foreign", "url", "duplicate", "instruction", "owner"]
)
def test_unreviewed_metadata_or_extra_instructions_fail_closed(case, field):
    ctx = deepcopy(case["context"])
    assets = ctx["normalized_content"]["assets"]
    a = assets[0]
    if field == "foreign":
        a["asset_id"] = "foreign"
    elif field == "url":
        a["url"] = "https://example.com/foreign.svg"
    elif field == "duplicate":
        assets.append(deepcopy(a))
    elif field == "instruction":
        section(ctx, "condition")["html"] += "<p>Округлите до сотых.</p>"
    else:
        a["asset_id"] = CONDITION if case["task"] == "315131" else SOLUTION
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("field", ["asset_key", "sha256", "url", "source_asset_id"])
def test_generated_identity_bound_to_actual_label_permutation(field):
    case = CASES[-1]
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = condition("B_1", "C_1", "A")
    metadata = list(generated(case, ctx))
    assert len(metadata) == 1
    metadata[0][field] = "foreign"
    with pytest.raises(ContentPlanError):
        plan(case, ctx, generated_solution_assets=tuple(metadata))
