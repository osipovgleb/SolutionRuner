"""Native two-part questions and deterministic preparation arguments."""

import json
from pathlib import Path

from midpoint_source_cases import section

from solution_runner.pipelines.core.content_runtime import _solution_assets
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.solids.spatial_distance_model import read_question

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_15_line_projection_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}


def arguments(group):
    ctx = next(c["context"] for c in CASES if c["task"] == group)
    return {
        "parent_asset_id": None,
        "parent_solution_html": section(ctx, "solution")["html"],
        "parent_solution_assets": _solution_assets(ctx),
    }


def plan(case, context=None, **overrides):
    ctx = case["context"] if context is None else context
    handler = get_handler(GROUPS[case["group"]]["rule"])
    generated = tuple(
        {
            "asset_key": s["asset_key"],
            "sha256": s["sha256"],
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in handler.diagram_specs(ctx)
    )
    return handler.plan(
        PlanInput(
            ctx,
            **{
                **arguments(case["group"]),
                "generated_solution_assets": generated,
                **overrides,
            },
        )
    )


def read(context):
    return read_question(section(context, "condition")["html"])


def changed_measurements(case, dimensions, context=None):
    import re
    from copy import deepcopy

    import sympy as sp

    from solution_runner.pipelines.solids.spatial_distance_model import condition_text

    ctx = deepcopy(case["context"] if context is None else context)
    a, b, h = map(sp.sympify, dimensions)
    raw = condition_text(section(ctx, "condition")["html"], None)
    if case["group"] == "507576":
        for name, val in zip(("AA_1", "AB", "BC"), (h, a, b), strict=True):
            raw = re.sub(
                name + r"\s*=\s*.+?(?=,|\.)", name + " = " + sp.latex(val), raw, count=1
            )
    else:
        raw = re.sub(
            r"(со сторонами AB\s*=\s*).+? и BC\s*=\s*.+?\.",
            lambda x: x[1] + sp.latex(a) + " и BC = " + sp.latex(b) + ".",
            raw,
        )
        raw = re.sub(
            r"(Длины боковых ребер пирамиды ).+?\.",
            lambda x: (
                x[1]
                + "SA = "
                + sp.latex(h)
                + ", SB = "
                + sp.latex(sp.sqrt(a * a + h * h))
                + ", SD = "
                + sp.latex(sp.sqrt(b * b + h * h))
                + "."
            ),
            raw,
        )
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    given = dict(read(ctx).given)
    assert (given["a"], given["b"], given.get("height", given.get("H"))) == (a, b, h)
    return ctx
