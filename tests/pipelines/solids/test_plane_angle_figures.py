"""Method fidelity, exact source figures and complete compound answers."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from plane_angle_source_cases import CASES, plan
from test_pyramid_midsections_lifecycle import without_figures

from solution_runner.pipelines.core.errors import ContentPlanError


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_method_order_labels_and_reviewed_figure_count(case):
    html = solution_html(plan(case))
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.find_all("img")) == (2 if case["task"] == "509502" else 1)
    if case["group"] == "509502":
        assert "Через A₁ проведём A₁M" in html
        assert soup.img["data-asset-id"] == "b7a50712-2b30-4405-93c2-de2b4c2f59e4"
        if case["task"] == "514243":
            assert "Метод координат" not in html and "тетраэдр" in html
        else:
            assert (
                html.index("По теореме Фалеса")
                < html.index("Метод координат")
                < html.index("в отрезках")
            )
    elif case["group"] == "513428":
        assert html.index("обратной теореме Пифагора") < html.index(
            "Верхнее основание параллельно ABC"
        )
    elif case["group"] == "507705":
        assert (
            html.index("средняя линия")
            < html.index("Проекция SB")
            < html.index("линейный угол")
        )
    else:
        assert "перпендикуляр" in html
        if case["task"] in {"512336", "512378"}:
            assert "проекцию L" in html and "смежный" in html


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unknown_assets_refuse_and_missing_figures_restore_sources(case):
    ctx = deepcopy(case["context"])
    a = ctx["normalized_content"]["assets"][0]
    old = a["asset_id"]
    a["asset_id"] = uid = "00000000-0000-4000-8000-000000000001"
    a["url"] = "/assets/" + uid
    for s in ctx["normalized_content"]["sections"]:
        s["html"] = s["html"].replace(old, uid)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    ctx = without_figures(case)
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    assert (
        len(ctx["normalized_content"]["assets"]) == 1
        and not plan(case, ctx).transformations
    )


@pytest.mark.parametrize("task", ("509586", "509607"))
def test_both_requested_answers_and_ratio_origin_ignore_wrong_saved_answers(task):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>Неверный ответ</p>"
    result = plan(case, ctx)
    assert r"\text{, считая от }B_1;\quad \arctan" in result.answer
    replay(ctx, result.transformations)
    assert (
        BeautifulSoup(section(ctx, "answer")["html"], "html.parser").span[
            "data-inline-latex"
        ]
        == result.answer
    )
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize("a", ("1", "3"))
def test_parent_projection_foot_outside_or_at_section_endpoint_needs_another_figure(a):
    from solution_runner.pipelines.solids.spatial_distance_model import condition_text

    case = next(c for c in CASES if c["task"] == "509586")
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert "AB = 9" in raw
    section(ctx, "condition")["html"] = (
        "<p>" + raw.replace("AB = 9", "AB = " + a) + "</p>"
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
