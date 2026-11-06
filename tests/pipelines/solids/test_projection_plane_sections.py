"""Native mathematical steps, idempotency and strict claim validation."""

from copy import deepcopy

import pytest
from midpoint_source_cases import replay, section, solution_html
from projection_plane_equation_oracle import verify
from projection_plane_source_cases import CASES, plan, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.spatial_distance_model import condition_text


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_equations_and_idempotent_preparation(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    verify(solution_html(result), read(ctx))
    assert ctx == case["context"]
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    for key in ("condition", "criteria", "source"):
        assert section(ctx, key) == section(case["context"], key)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_requirement_and_parent_drift_refuse(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также объём.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("701579", "16: 9", "15: 9"),
        ("701579", "AM = AK = 6", "AM = AK = 11"),
        ("484562", "прямая B_1D", "прямая BD"),
        ("507695", "60°", "45°"),
        ("511476", "равна 3", "равна 2"),
        ("507699", "прямая призма", "наклонная призма"),
    ],
)
def test_false_claims_and_impossible_geometry_refuse(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None).replace(
        r"\colon", ":"
    )
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("task", ("507581", "507592", "484561"))
@pytest.mark.parametrize("dims", ((3, 5, 7), (8, 12, 8), (9, 9, 6)))
def test_changed_box_lengths_use_actual_perpendicular_foot_and_labels(task, dims):
    import re

    import sympy as sp
    from projection_plane_geometry import geometry
    from projection_plane_source_cases import GROUPS

    from solution_runner.pipelines.core.handler_registry import get_handler

    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    for name, val in zip(("AB", "BC", "CC_1"), dims, strict=True):
        raw = re.sub(
            r"\b" + name + r"\s*=\s*.+?(?=,|\.)", name + " = " + str(val), raw
        )
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    m = read(ctx)
    p, _, _ = geometry(m)
    for i, axis in enumerate("xyz"):
        assert (
            sp.simplify(m.q["E_" + axis] - p["H" if task == "484561" else "E"][i]) == 0
        )
    result = plan(case, ctx)
    verify(solution_html(result), m)
    specs = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx)
    assert len(specs) == (0 if task == "484561" else 1)
    if task in {"507581", "507592"}:
        assert (
            "середина" in solution_html(result)
            if (dims[0] == (dims[2] if task == "507581" else dims[1]))
            else "середина" not in solution_html(result)
        )
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize(
    "task", ("701579", "701652", "701646", "507695", "511476", "507699")
)
def test_scaled_solids_preserve_angle_and_every_calculation(task):
    import re

    import sympy as sp

    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    old = read(ctx)
    raw = condition_text(section(ctx, "condition")["html"], None)
    if case["group"] == "701579":
        raw = re.sub(
            r"(все ребра равны ).+?\.",
            lambda x: x[1] + str(dict(old.given)["a"] * 2) + ".",
            raw,
        )
        raw = re.sub(
            r"(AM\s*=\s*AK\s*=\s*).+?\.",
            lambda x: x[1] + str(dict(old.given)["t"] * 2) + ".",
            raw,
        )
    else:
        for pattern, key in (
            (r"((?:сторона|ребро) основания равн[ао] ).+?(?=,|\.)", "a"),
            (r"(ромб со стороной ).+? и", "a"),
            (r"(высота призмы равна ).+?(?=,|\.)", "height"),
            (r"(Высота призмы равна ).+?\.", "height"),
        ):
            raw = re.sub(
                pattern,
                lambda x, key=key: (
                    x[1]
                    + str(dict(old.given)[key] * 2)
                    + (
                        " и"
                        if "ромб со стороной" in x[1]
                        else "."
                        if x[1].startswith("Высота")
                        else ""
                    )
                ),
                raw,
            )
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    m = read(ctx)
    assert dict(m.given)["a"] == 2 * dict(old.given)["a"]
    assert sp.simplify(m.answer - old.answer) == 0
    verify(solution_html(plan(case, ctx)), m)


def test_reversed_volume_ratio_proves_the_explicitly_reversed_polyhedra():
    case = next(c for c in CASES if c["task"] == "701579")
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None).replace(
        r"\colon", ":"
    )
    assert "16: 9" in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace("16: 9", "9: 16") + "</p>"
    m = read(ctx)
    assert m.names == ("corner",)
    verify(solution_html(plan(case, ctx)), m)
