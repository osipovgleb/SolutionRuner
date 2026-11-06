"""Full native plans preserve every verified scalar equation and remain idempotent."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from line_projection_equation_oracle import verify as verify_projection
from line_projection_source_cases import CASES, plan, read
from midpoint_source_cases import replay, section, solution_html
from test_half_prism_pyramid_models import verify as verify_cut

from solution_runner.pipelines.core.errors import ContentPlanError


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_plan_equation_and_idempotency(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    html = solution_html(result)
    m = read(ctx)
    if case["group"] in {"500064", "505237"}:
        verify_cut(m, html)
    else:
        verify_projection(html, m)
    assert ctx == case["context"]
    assert not any(
        x in BeautifulSoup(html, "html.parser").get_text()
        for x in (r"\frac", r"\sqrt", "\f")
    )
    if case["group"] == "513098":
        assert html.count("SA ⟂ AB") == 1
        if case["task"] == "661318":
            assert html.index("Пусть O") < html.index("Метод координат")
        elif case["task"] == "513098":
            assert result.answer == r"30^{\circ}"
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    for key in ("condition", "criteria", "source"):
        assert section(ctx, key) == section(case["context"], key)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_question_and_parent_drift_refuse(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также площадь.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_assets=())
