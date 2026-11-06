"""Full native equations and immutable, idempotent preparation."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from midsection_plane_equation_oracle import verify
from midsection_plane_source_cases import CASES, plan, read


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_equations_and_idempotency(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    verify(solution_html(result), read(ctx))
    assert ctx == case["context"]
    assert not any(
        x in BeautifulSoup(solution_html(result), "html.parser").get_text()
        for x in [r"\frac", r"\sqrt", "{,}"]
    )
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    for key in ("condition", "criteria", "source"):
        assert section(ctx, key) == section(case["context"], key)
    assert section(ctx, "answer")["asset_keys"] == []


def scaled(raw, m, factor):
    import re

    import sympy as sp

    g = dict(m.given)
    if m.mode == "square_prism_opposite_vertex_plane_angle":
        for phrase, key in [
            ("стороны основания равны ", "a"),
            ("боковые ребра равны ", "height"),
        ]:
            raw = re.sub(
                "(" + phrase + r").+?(?=,|\.)",
                lambda x, key=key: x[1] + sp.latex(g[key] * factor),
                raw,
                count=1,
            )
        return raw
    for label, key in [("AB", "a"), ("AD", "b"), ("SA", "e")]:
        if key in g:
            raw = re.sub(
                r"(\b" + label + r"\s*(?:равна|равно|=)\s*).+?(?=,|\.)",
                lambda x, key=key: x[1] + sp.latex(g[key] * factor),
                raw,
                count=1,
            )
    if m.mode == "box_skew_distance_normal_angle":
        return re.sub(
            r"(если расстояние между прямыми AC и B_1D_1 равно ).+?\.$",
            lambda x: x[1] + sp.latex(g["height"] * factor) + ".",
            raw,
        )
    if m.mode == "triangle_pyramid_midpoint_plane_angle":
        return re.sub(
            r"(высота SH(?:, проведенная к основанию,)? равна ).+?(?=,|\.)",
            lambda x: x[1] + sp.latex(g["height"] * factor),
            raw,
            count=1,
        )
    return raw


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("factor", ("3/2", "3"))
def test_changed_lengths_scale_independent_geometry_and_keep_angle(case, factor):
    import sympy as sp

    from solution_runner.pipelines.solids.spatial_distance_model import condition_text

    ctx = deepcopy(case["context"])
    old = read(ctx)
    raw = condition_text(section(ctx, "condition")["html"], None)
    changed = scaled(raw, old, sp.Rational(factor))
    assert changed != raw
    section(ctx, "condition")["html"] = "<p>" + changed + "</p>"
    m = read(ctx)
    result = plan(case, ctx)
    verify(solution_html(result), m)
    assert sp.simplify(m.answer - old.answer) == 0


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_requirements_and_changed_parent_solution_refuse(case):
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
        ("485981", "A_1D_1 и BD", "A_1D_1 и AB"),
        ("485981", "перпендикулярно прямой BD_1", "параллельно прямой BD_1"),
        ("485981", "B_1D_1 равно 13", "B_1D_1 равно 0"),
        ("500132", "точки A и C_1", "точки A и B_1"),
        ("500132", "1: 2", "0: 2"),
        ("500132", "1: 2", "1: 1"),
        ("563633", "середина AS", "середина AB"),
        ("563633", "равна 14", "равна 0"),
        ("680003", "высота SH равна 9", "высота SH равна -9"),
        ("641933", "параллельна прямой BC", "перпендикулярна прямой BC"),
        ("641933", "боковое ребро SA равно 7", "боковое ребро SA равно 3"),
        ("651030", "точки L и N", "точки L и M"),
        ("651063", "плоскостями α и SBC", "плоскостями α и SAB"),
        ("681090", "1: 3", "0: 3"),
    ),
)
def test_impossible_solids_changed_proofs_and_unsupported_equal_height_scene_refuse(
    task, old, new
):
    from solution_runner.pipelines.core.errors import ContentPlanError
    from solution_runner.pipelines.solids.spatial_distance_model import condition_text

    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("task", ("641933", "651030", "651063", "681090"))
def test_different_valid_section_ratio_retains_parallelism_and_plane_angle(task):
    import sympy as sp

    from solution_runner.pipelines.solids.spatial_distance_model import condition_text

    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    old = read(ctx)
    g = dict(old.given)
    raw = condition_text(section(ctx, "condition")["html"], None).replace(
        r"\colon", ":"
    )
    given = str(g["p"]) + ": " + str(g["q"])
    assert given in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(given, "1: 2") + "</p>"
    m = read(ctx)
    assert m.given != old.given
    result = plan(case, ctx)
    verify(solution_html(result), m)
    assert sp.simplify(m.answer - old.answer) == 0
