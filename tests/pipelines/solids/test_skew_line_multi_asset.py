"""Multiple generated illustrations keep separate hashes, ownership and proof positions."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from line_projection_source_cases import CASES as OLD_CASES
from line_projection_source_cases import plan as old_plan
from midpoint_source_cases import replay, section, solution_html
from skew_line_source_cases import CASES, GROUPS, arguments, plan
from test_midpoint_area_lifecycle import OfflineGateway
from test_pyramid_midsections_lifecycle import without_figures

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.quadrilaterals.quantity_content import read_content


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_prepare_freezes_every_native_asset_without_upload_or_write(case):
    gateway = OfflineGateway(case)
    record = _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=GROUPS[case["group"]]["rule"],
        **arguments(case["group"]),
    )
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == plan(case).answer
    diagrams = record["generated_diagrams"]
    assert len(diagrams) == (
        3 if case["task"] == "530402" else 1 if case["task"] == "511402" else 0
    )
    assert len({s["asset_key"] for s in diagrams}) == len(diagrams)
    assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_figures_restore_all_parent_methods_and_resume(case):
    ctx = without_figures(case)
    result = plan(case, ctx)
    html = solution_html(result)
    expected = 4 if case["group"] == "699395" else 2 if case["group"] == "505387" else 1
    assert len(BeautifulSoup(html, "html.parser").find_all("img")) == expected
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize("task", ("530402", "511402"))
@pytest.mark.parametrize("mutation", ("hash", "duplicate", "missing"))
def test_each_generated_slot_requires_its_own_exact_hash(task, mutation):
    case = next(c for c in CASES if c["task"] == task)
    specs = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(case["context"])
    generated = [
        {
            "asset_key": s["asset_key"],
            "sha256": s["sha256"],
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in specs
    ]
    if mutation == "hash":
        generated[-1]["sha256"] = "0" * 64
    elif mutation == "duplicate":
        generated.append(deepcopy(generated[0]))
    else:
        generated.pop()
    with pytest.raises(ContentPlanError):
        plan(case, generated_solution_assets=tuple(generated))


def test_shared_quantity_reader_still_rejects_repetitions_without_explicit_opt_in():
    parent = next(c for c in CASES if c["task"] == "699395")
    with pytest.raises(ContentPlanError):
        read_content(parent["context"], {"image_1", "image_2", "image_3"})


@pytest.mark.parametrize("mutation", ("source", "section"))
def test_reviewed_repeat_cannot_change_its_source_or_owning_section(mutation):
    case = next(c for c in CASES if c["task"] == "699395")
    ctx = deepcopy(case["context"])
    soup = BeautifulSoup(section(ctx, "solution")["html"], "html.parser")
    repeated = soup.find_all("img", attrs={"data-asset-key": "image_2"})[-1]
    if mutation == "source":
        repeated["src"] = "/assets/wrong"
    else:
        section(ctx, "condition")["html"] += str(repeated)
    section(ctx, "solution")["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_old_spatial_modes_do_not_accept_the_new_repeat_or_generated_keys():
    case = next(c for c in OLD_CASES if c["task"] == "513098")
    for mode in ("repeat", "new_key"):
        ctx = deepcopy(case["context"])
        solution = section(ctx, "solution")
        if mode == "repeat":
            image = BeautifulSoup(solution["html"], "html.parser").img
            image["data-asset-key"] = "image_2"
            image["data-transformation-target-id"] = "asset:image_2"
            asset = deepcopy(ctx["normalized_content"]["assets"][0])
            asset["asset_key"] = "image_2"
            ctx["normalized_content"]["assets"].append(asset)
            solution["html"] += str(image) + str(image)
            solution["asset_keys"].append("image_2")
        else:
            asset = ctx["normalized_content"]["assets"][0]
            asset["asset_key"] = "box_distance_solution_2"
            solution["html"] = (
                solution["html"]
                .replace(
                    'data-asset-key="image_1"',
                    'data-asset-key="box_distance_solution_2"',
                )
                .replace("asset:image_1", "asset:box_distance_solution_2")
            )
            solution["asset_keys"] = ["box_distance_solution_2"]
        with pytest.raises(ContentPlanError):
            old_plan(case, ctx)
