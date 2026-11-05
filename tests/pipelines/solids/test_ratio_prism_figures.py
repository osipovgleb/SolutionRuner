"""Reviewed multi-slot roles, duplicate answer pictures and prime notation."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from ratio_prism_source_cases import CASES, plan
from test_pyramid_midsections_lifecycle import without_figures

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.distance_answer_figures import clean_context
from solution_runner.pipelines.solids.distance_figures import selection
from solution_runner.pipelines.solids.spatial_distance_model import condition_text
from solution_runner.pipelines.solids.spatial_distance_sources import compatible


@pytest.mark.parametrize(
    "task,keys",
    (
        ("681196", ["image_2", "image_1"]),
        ("681272", ["image_1"]),
        ("681300", ["image_1"]),
    ),
)
def test_shared_native_asset_keeps_both_parent_slots_and_child_single_scene(task, keys):
    case = next(c for c in CASES if c["task"] == task)
    m = selection(case["context"])[0]
    html = solution_html(plan(case))
    soup = BeautifulSoup(html, "html.parser")
    assert [i["data-asset-key"] for i in soup.find_all("img")] == keys
    assert html.index("SC=") < html.index("Другой способ доказательства")
    assert "Начало координат выберем в D" in html
    assert compatible(
        m, "99e7eb5f-b4ab-4624-97a3-84c0934a9ae8", "solution", m.symbols["main_slot"]
    )
    if task == "681196":
        assert not compatible(
            m, "99e7eb5f-b4ab-4624-97a3-84c0934a9ae8", "solution", "image_1"
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_scenes_restore_matching_names_without_adding_unneeded_second(case):
    ctx = without_figures(case)
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    assert len(ctx["normalized_content"]["assets"]) == 1
    assert not plan(case, ctx).transformations


def test_known_answer_picture_duplicate_is_read_only_and_removed_even_for_matching_number():
    case = next(c for c in CASES if c["task"] == "681196")
    ctx = deepcopy(case["context"])
    answer = section(ctx, "answer")
    soup = BeautifulSoup(answer["html"], "html.parser")
    image = str(soup.img)
    answer["html"] = "<p>8</p>" + image
    before = deepcopy(ctx)
    clean = clean_context(ctx)
    assert ctx == before and clean is not ctx
    assert not BeautifulSoup(section(clean, "answer")["html"], "html.parser").find(
        "img"
    )
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    assert section(ctx, "answer")["asset_keys"] == []
    assert not BeautifulSoup(section(ctx, "answer")["html"], "html.parser").find("img")
    assert (
        len(
            BeautifulSoup(section(ctx, "solution")["html"], "html.parser").find_all(
                "img"
            )
        )
        == 2
    )
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize(
    "change",
    (
        "foreign_url",
        "foreign_source",
        "missing_solution_reference",
        "extra_attribute",
        "unknown_answer_figure",
    ),
)
def test_nonidentical_or_unreviewed_answer_figure_is_refused(change):
    case = next(c for c in CASES if c["task"] == "681196")
    ctx = deepcopy(case["context"])
    answer = section(ctx, "answer")
    soup = BeautifulSoup(answer["html"], "html.parser")
    image = soup.img
    if change == "foreign_url":
        image["src"] = "/assets/foreign"
    elif change == "foreign_source":
        image["data-asset-id"] = "foreign"
    elif change == "extra_attribute":
        image["data-foreign"] = "changed"
    elif change == "unknown_answer_figure":
        image["data-asset-key"] = "image_2"
        image["data-asset-id"] = "99e7eb5f-b4ab-4624-97a3-84c0934a9ae8"
        image["src"] = "/assets/99e7eb5f-b4ab-4624-97a3-84c0934a9ae8"
        image["data-transformation-target-id"] = "asset:image_2"
        answer["asset_keys"] = ["image_2"]
    else:
        solution = section(ctx, "solution")
        other = BeautifulSoup(solution["html"], "html.parser")
        other.find("img", attrs={"data-asset-key": "image_1"}).decompose()
        solution["html"] = str(other)
        solution["asset_keys"].remove("image_1")
    answer["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("task", ("681272", "507887", "500968", "501124"))
def test_unknown_or_unreviewed_slot_is_not_accepted_by_the_extended_slot_support(task):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    a = ctx["normalized_content"]["assets"][0]
    old = a["asset_key"]
    a["asset_key"] = "image_3"
    solution = section(ctx, "solution")
    solution["html"] = solution["html"].replace(old, "image_3")
    solution["asset_keys"] = ["image_3"]
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_prime_proof_keeps_the_explicit_condition_vocabulary():
    case = next(c for c in CASES if c["task"] == "501124")
    html = solution_html(plan(case))
    assert "A&#x27;" in html or "A'" in html
    assert "A_1" not in html and "₁" not in html


@pytest.mark.parametrize(
    "inner",
    ("<i>ABCA''B'C'</i>", "<i>ABCA'B'X'</i>", "<i data-foreign='yes'>ABCA'B'C'</i>"),
)
def test_unreviewed_prime_or_italic_markup_is_refused(inner):
    with pytest.raises(ContentPlanError):
        condition_text("<p>" + inner + "</p>", None)
