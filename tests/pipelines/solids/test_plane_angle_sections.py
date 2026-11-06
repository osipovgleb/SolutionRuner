"""Native full solutions, every formula, immutable input and repeat preparation."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from plane_angle_equation_oracle import verify
from plane_angle_source_cases import CASES, plan, read


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_equations_and_idempotency(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    verify(solution_html(result), read(ctx))
    assert ctx == case["context"]
    plain = BeautifulSoup(solution_html(result), "html.parser").get_text()
    assert not any(x in plain for x in (r"\frac", r"\sqrt", "{,}"))
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    for key in ("condition", "criteria", "source"):
        assert section(ctx, key) == section(case["context"], key)
    assert section(ctx, "answer")["asset_keys"] == []


def scaled_condition(raw, m, factor):
    import re

    import sympy as sp

    g = dict(m.given)
    if m.mode.startswith("cube_parallel"):
        raw = re.sub(
            r"(все ребра равны |Ребро куба ABCDA_1B_1C_1D_1 равно ).+?\.",
            lambda x: x[1] + sp.latex(g["a"] * factor) + ".",
            raw,
            count=1,
        )
        return re.sub(
            r"KB\s*=\s*.+?\.",
            lambda _: "KB=" + sp.latex(g["k"] * factor) + ".",
            raw,
            count=1,
        )
    if m.mode.startswith("triangle_prism_endpoint"):
        return re.sub(
            r"(все ребра которой равны ).+?\.",
            lambda x: x[1] + sp.latex(g["a"] * factor) + ".",
            raw,
            count=1,
        )
    labels = (
        (("AB", "a"), ("SC", "edge"))
        if "edge" in g
        else (("AB", "a"), ("AD", "b"), ("AA_1", "height"))
    )
    for label, key in labels:
        raw = re.sub(
            r"\b" + label + r"\s*=\s*.+?(?=,|\.)",
            lambda _, label=label, key=key: label + "=" + sp.latex(g[key] * factor),
            raw,
            count=1,
        )
    return raw


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("factor", ("3/2", "3"))
def test_changed_lengths_have_independent_geometry_and_expected_dimension(case, factor):
    import sympy as sp

    from solution_runner.pipelines.solids.spatial_distance_model import condition_text

    ctx = deepcopy(case["context"])
    original = read(ctx)
    factor = sp.Rational(factor)
    raw = condition_text(section(ctx, "condition")["html"], None)
    changed = scaled_condition(raw, original, factor)
    assert raw != changed
    section(ctx, "condition")["html"] = "<p>" + changed + "</p>"
    m = read(ctx)
    result = plan(case, ctx)
    verify(solution_html(result), m)
    assert (
        sp.simplify(
            m.answer
            - original.answer * factor ** (3 if m.mode.endswith("volume") else 0)
        )
        == 0
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_requirements_and_changed_parent_method_refuse(case):
    from solution_runner.pipelines.core.errors import ContentPlanError

    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также объём.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")


@pytest.mark.parametrize(
    "task,old,new",
    (
        ("509502", "KB = 3", "KB = 2"),
        ("509502", "KB = 3", "KB = 4"),
        ("509502", "2: 1", "3: 1"),
        ("509502", "параллельная прямой BD_1", "параллельная прямой B_1D_1"),
        ("514243", "большей из двух частей", "меньшей из двух частей"),
        ("507705", "SC = 6", "SC = 4"),
        ("507705", "середина ребра SC", "середина ребра SD"),
        ("512336", "1: 5", "2: 5"),
        ("512378", "середина ребра B_1C_1", "середина ребра A_1B_1"),
        ("513428", "все ребра которой равны 4", "все ребра которой равны -4"),
        ("513428", "плоскостью ABC", "плоскостью ABB_1"),
    ),
)
def test_false_claims_degeneracy_and_wrong_reference_face_refuse(task, old, new):
    from solution_runner.pipelines.core.errors import ContentPlanError
    from solution_runner.pipelines.solids.spatial_distance_model import condition_text

    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("task", ("509586", "512336"))
def test_non_isosceles_transverse_sections_keep_projection_and_all_equations(task):
    from solution_runner.pipelines.solids.spatial_distance_model import condition_text

    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    m = read(ctx)
    raw = condition_text(section(ctx, "condition")["html"], None)
    old = "AD = " + str(m.q["b"])
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, "AD = 7") + "</p>"
    result = plan(case, ctx)
    verify(solution_html(result), read(ctx))
    html = solution_html(result)
    assert "равнобедренной трапеции" not in html and "L — середина" not in html
