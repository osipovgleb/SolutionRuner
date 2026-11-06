"""Native preparation checks proofs, exact source reuse, correction and idempotency."""

from copy import deepcopy

import pytest
from midpoint_projection_equations import verify
from midpoint_projection_source_cases import CASES, plan, read
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.distance_figures import selection


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_plans_verify_every_equation_and_are_idempotent(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    verify(read(ctx), solution_html(result))
    assert ctx == case["context"]
    if case["task"] == "485943":
        assert result.answer == r"45^{\circ}"
    if case["task"] == "511324":
        html = solution_html(result)
        assert "8a9c6676-fa04-4271-a557-ccf630c55a82" in html
        assert "8dac3233-9ae3-430c-831b-d3d74edc87eb" not in html
        assert "9f5b6d3e-48ab-40a6-a853-da8f7033aaef" in html
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    for key in ("condition", "criteria", "source"):
        assert section(ctx, key) == section(case["context"], key)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_parent_drift_and_extra_question_fail_closed(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также площадь.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_assets=())


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_retain_all_compatible_native_figures(case):
    _, _, _, assets, figures = selection(case["context"])
    selected = {key: source for _, _, source, key, drawing in figures if not drawing}
    for key, asset in assets.items():
        if case["task"] == "511324" and key == "image_1":
            assert selected[key] == "8a9c6676-fa04-4271-a557-ccf630c55a82"
        else:
            assert selected[key] == asset["asset_id"]
