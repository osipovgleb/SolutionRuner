"""Mathematical cells, exact asset reuse and local-only diagram preparation."""

import hashlib
from copy import deepcopy
from fractions import Fraction
from itertools import product
from xml.etree import ElementTree as ET

import pytest
from test_source_samples import CASES

from solution_runner.pipelines.probability.conditioned_dice import (
    Case,
    asset_requirements,
    build_context_repair_plan,
    diagram_specs,
    outcomes,
    render_svg,
)


@pytest.mark.parametrize("excluded", range(1, 7))
@pytest.mark.parametrize(
    "kind,value", [("sum", k) for k in range(1, 14)] + [("parity", 0), ("parity", 1)]
)
def test_svg_cells_and_markers_match_an_independent_probability_space(
    excluded, kind, value
):
    case = Case(excluded, kind, value)
    domain = {
        (a, b)
        for a, b in product(range(1, 7), repeat=2)
        if a != excluded and b != excluded
    }
    favorable = {
        row
        for row in domain
        if (sum(row) == value if kind == "sum" else row[0] % 2 == row[1] % 2 == value)
    }
    root = ET.fromstring(render_svg(case))

    def cells(role):
        group = next(e for e in root if e.get("data-role") == role)
        return {tuple(map(int, e.attrib["data-outcome"].split(","))) for e in group}

    assert len(domain) == 25
    assert cells("admissible-outcomes") == domain
    assert cells("favorable-outcomes") == favorable
    assert set(outcomes(case)[1]) == favorable
    if kind == "parity":
        one = sum(x != excluded and x % 2 == value for x in range(1, 7))
        assert Fraction(len(favorable), 25) == Fraction(one, 5) ** 2


def test_reviewed_source_tables_are_reused_exactly_without_additions():
    cases = [c for c in CASES if c["group"] in ("508769", "676847")]
    assert len(cases) == 6
    for case in cases:
        context = deepcopy(case["context"])
        original = deepcopy(context)
        (requirement,) = asset_requirements(context)
        (asset,) = context["normalized_content"]["assets"]
        assert requirement["source_asset_id"] == asset["asset_id"]
        assert diagram_specs(context) == ()
        plan = build_context_repair_plan(context)
        assert asset["asset_id"] in plan.solution_html
        assert not any(
            t["transformation_target_id"].startswith("asset:")
            for t in plan.transformations
        )
        assert context == original
        if case["group"] == "676847":
            assert "Другой способ" in plan.solution_html
            assert "независимыми" in plan.solution_html


def _new_case():
    case = deepcopy(next(c for c in CASES if c["task"] == "508769")["context"])
    condition = next(
        s for s in case["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        "<p>Игральную кость бросили два раза. Известно, что четыре очка не выпали ни разу. Найдите при этом условии вероятность события «сумма выпавших очков окажется равна 7».</p>"
    )
    return case


def test_new_mathematical_case_builds_a_verified_local_spec_and_is_idempotent():
    context = _new_case()
    original = deepcopy(context)
    assert asset_requirements(context) == ()
    (spec,) = diagram_specs(context)
    assert hashlib.sha256(spec["svg_text"].encode()).hexdigest() == spec["sha256"]
    generated = {
        **{k: v for k, v in spec.items() if k != "svg_text"},
        "source_asset_id": "local-preview",
        "url": "/assets/local-preview",
    }
    plan = build_context_repair_plan(context, generated_solution_assets=(generated,))
    assert plan.answer == "0,16"
    assert context == original
    with pytest.raises(ValueError):
        build_context_repair_plan(context)
    with pytest.raises(ValueError):
        build_context_repair_plan(
            context, generated_solution_assets=({**generated, "sha256": "wrong"},)
        )
    content = context["normalized_content"]
    for change in plan.transformations:
        if change["transformation_target_id"].startswith("asset:"):
            asset = change["value"]
            content["assets"].append(
                {
                    **asset,
                    "transformation_target_id": change["transformation_target_id"],
                }
            )
        else:
            target = next(
                s
                for s in content["sections"]
                if s["transformation_target_id"] == change["transformation_target_id"]
            )
            target.update(change["value"])
    assert (
        build_context_repair_plan(
            context, generated_solution_assets=(generated,)
        ).transformations
        == ()
    )


def test_condition_asset_or_inconsistent_extra_instruction_is_rejected():
    context = _new_case()
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["asset_keys"] = ["image_1"]
    with pytest.raises(ValueError):
        diagram_specs(context)
    condition["asset_keys"] = []
    condition["html"] += "<p>В ответе запишите удвоенную вероятность.</p>"
    with pytest.raises(ValueError):
        diagram_specs(context)
