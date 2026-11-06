"""Full native plans preserve every method and each independently generated picture."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from skew_line_equation_oracle import verify
from skew_line_source_cases import CASES, GROUPS, plan, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.distance_figures import selection


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_equations_figure_slots_and_idempotent_plan(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    html = solution_html(result)
    verify(html, read(case))
    assert ctx == case["context"]
    assert "\\" not in BeautifulSoup(html, "html.parser").get_text()
    specs = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx)
    assert len(specs) == (
        3 if case["task"] == "530402" else 1 if case["task"] == "511402" else 0
    )
    keys = [s["asset_key"] for s in specs]
    assert len(keys) == len(set(keys))
    if case["task"] == "530402":
        assert keys == [
            "box_distance_solution_1",
            "box_distance_solution_2",
            "box_distance_solution_3",
        ]
        assert html.count('data-asset-key="box_distance_solution_2"') == 2
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    for key in ("condition", "criteria", "source"):
        assert section(ctx, key) == section(case["context"], key)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_parent_drift_extra_requirements_and_missing_generated_assets_refuse(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также площадь.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_assets=())
    if case["task"] in {"530402", "511402"}:
        with pytest.raises(ContentPlanError):
            plan(case, generated_solution_assets=())


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_valid_native_figures_are_preserved_and_wrong_order_is_repaired(case):
    _, _, _, assets, figures = selection(case["context"])
    chosen = {key: source for _, _, source, key, drawing in figures if not drawing}
    for key, asset in assets.items():
        if case["task"] in {"699395", "699399"} and key == "image_1":
            assert chosen[key] == "5e775e0f-9a27-448c-8dbb-414e9ed8f975"
        elif case["task"] == "530402":
            assert key not in chosen
        else:
            assert chosen[key] == asset["asset_id"]
