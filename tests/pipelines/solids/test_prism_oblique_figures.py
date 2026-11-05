"""All parent methods, four strict slots and canonical ratio answers."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from prism_oblique_source_cases import CASES, plan
from test_pyramid_midsections_lifecycle import without_figures

from solution_runner.pipelines.core.errors import ContentPlanError


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_method_order_and_reviewed_scene_counts(case):
    html = solution_html(plan(case))
    images = BeautifulSoup(html, "html.parser").find_all("img")
    if case["group"] == "634951":
        assert [i["data-asset-key"] for i in images] == [
            "image_1",
            "image_2",
            "image_3",
            "image_4",
        ]
        assert (
            html.index("при помощи векторов")
            < html.index("методом координат")
            < html.index("Построение сечения")
            < html.index("Геометрическое решение")
        )
        assert "2955ecc6-d800-4537-911e-a9b2c71cb32f" not in html
        assert html.index("C_1K=") < html.index("TK+KD_1=")
    else:
        expected = max(1, len(case["context"]["normalized_content"]["assets"]))
        assert len(images) == expected
        if case["group"] == "681165":
            assert (
                html.index("по формуле площади") < html.index("Метод координат")
                if case["task"] == "681296"
                else html.index("Треугольник MKC₁ прямоугольный")
                < html.index("Метод координат")
            )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unknown_assets_are_refused_before_any_plan(case):
    ctx = deepcopy(case["context"])
    if not ctx["normalized_content"]["assets"]:
        result = plan(case, ctx)
        replay(ctx, result.transformations)
    asset = ctx["normalized_content"]["assets"][0]
    old, uid = asset["asset_id"], "00000000-0000-4000-8000-000000000001"
    asset["asset_id"], asset["url"] = uid, "/assets/" + uid
    for sec in ctx["normalized_content"]["sections"]:
        sec["html"] = sec["html"].replace(old, uid)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("task", ("676903", "681165", "501752"))
def test_fourth_slot_is_not_accepted_outside_the_reviewed_four_scene_mode(task):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    source = next(c for c in CASES if c["task"] == "634951")["context"]
    asset = deepcopy(source["normalized_content"]["assets"][-1])
    image = BeautifulSoup(section(source, "solution")["html"], "html.parser").find(
        "img", attrs={"data-asset-key": "image_4"}
    )
    ctx["normalized_content"]["assets"].append(asset)
    section(ctx, "solution")["asset_keys"].append("image_4")
    section(ctx, "solution")["html"] += str(image)
    with pytest.raises(ContentPlanError, match="fourth spatial diagram"):
        plan(case, ctx)


@pytest.mark.parametrize("change", ("wrong_slot", "answer_owner", "foreign_url"))
def test_fourth_scene_keeps_its_exact_slot_owner_and_identity(change):
    case = next(c for c in CASES if c["task"] == "634951")
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][-1]
    solution = section(ctx, "solution")
    soup = BeautifulSoup(solution["html"], "html.parser")
    image = soup.find("img", attrs={"data-asset-key": "image_4"})
    if change == "wrong_slot":
        wrong_source = ctx["normalized_content"]["assets"][-2]["asset_id"]
        asset["asset_id"] = wrong_source
        asset["url"] = "/assets/" + wrong_source
        image["data-asset-id"] = wrong_source
        image["src"] = asset["url"]
    elif change == "foreign_url":
        image["src"] = "/assets/foreign"
    else:
        image.extract()
        solution["asset_keys"].remove("image_4")
        section(ctx, "answer")["html"] += str(image)
        section(ctx, "answer")["asset_keys"] = ["image_4"]
    solution["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("task", ("681580", "694819", "501752"))
def test_missing_solution_or_answer_is_restored_from_the_parent(task):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    assert section(ctx, "solution") and section(ctx, "answer")
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] == "634951"], ids=lambda c: c["task"]
)
def test_missing_scenes_restore_all_parent_methods_and_explicit_answer_origin(case):
    ctx = without_figures(case)
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    assert len(ctx["normalized_content"]["assets"]) == 4
    answer = section(ctx, "answer")
    soup = BeautifulSoup(answer["html"], "html.parser")
    assert (
        soup.span["data-inline-latex"] == result.answer and "считая от" in result.answer
    )
    assert not plan(case, ctx).transformations


def test_missing_low_edge_point_scene_uses_the_reviewed_lower_M_variant():
    case = next(c for c in CASES if c["task"] == "694819")
    soup = BeautifulSoup(solution_html(plan(case)), "html.parser")
    assert soup.img["data-asset-id"] == "21b9d632-f537-4b72-bca3-dce94e1dfee9"
    assert "Метод координат" in str(soup)
