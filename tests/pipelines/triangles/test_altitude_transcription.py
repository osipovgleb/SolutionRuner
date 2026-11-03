"""An audited lost fraction must be repaired visibly, atomically and exactly."""

import hashlib
from copy import deepcopy

import pytest
from altitude_source_cases import CASES, plan, section
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.triangles.right import altitude_transcription
from solution_runner.pipelines.triangles.right.altitude_input import canonical_condition
from solution_runner.pipelines.triangles.right.altitude_solver import AltitudeSolveError

CASE = next(c for c in CASES if c["task"] == "4815")
RECORD = altitude_transcription._DATA["entries"][0]
SOURCE = "a99e8a50-d3f3-4b22-ab0a-0a334b60e1fc"


def test_verified_restoration_is_a_visible_condition_change_and_preserves_the_figure():
    original = deepcopy(CASE["context"])
    result = plan(CASE)
    assert CASE["context"] == original and result.answer == "1,8"
    repairs = [
        t
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:condition")
    ]
    assert len(repairs) == 1 and repairs[0]["operation"] == "rewrite"
    assert repairs[0]["value"] == {
        "title": "Условие",
        "html": RECORD["after_html"],
        "asset_keys": ["image_1"],
    }
    before = BeautifulSoup(RECORD["before_html"], "html.parser")
    after = BeautifulSoup(RECORD["after_html"], "html.parser")
    assert str(before.find("img")) == str(after.find("img"))
    assert not any(
        t["transformation_target_id"].startswith("asset:")
        for t in result.transformations
    )
    with pytest.raises(AltitudeSolveError):
        canonical_condition(RECORD["before_html"], source=SOURCE)


@pytest.mark.parametrize("change", ["space", "instruction", "value", "script"])
def test_unreviewed_changes_to_the_damaged_condition_are_not_guessed(change):
    context = deepcopy(CASE["context"])
    condition = section(context, "condition")
    if change == "value":
        condition["html"] = condition["html"].replace("</span>3,", "</span>4,")
    else:
        condition["html"] += {
            "space": " ",
            "instruction": "<p>Удвойте ответ.</p>",
            "script": "<script>answer=999</script>",
        }[change]
    original = deepcopy(context)
    with pytest.raises(ContentPlanError):
        plan(CASE, context)
    assert context == original


def test_restoration_uses_the_exact_source_condition_instead_of_task_id_or_saved_solution():
    context = deepcopy(CASE["context"])
    context["problem_id"] = "unrelated-problem-id"
    for key in ("answer", "solution"):
        section(context, key)["html"] = "<p>Нет данных для восстановления.</p>"
    result = plan(CASE, context)
    assert result.answer == "1,8"
    assert (
        next(
            t["value"]["html"]
            for t in result.transformations
            if t["transformation_target_id"].startswith("section:condition")
        )
        == RECORD["after_html"]
    )


def test_reviewed_transcription_records_original_svg_provenance_and_no_saved_answer():
    assert (
        hashlib.sha256(RECORD["before_html"].encode()).hexdigest()
        == RECORD["condition_sha256"]
    )
    assert RECORD["after_html"] == CASE["verified_condition_html"]
    assert RECORD["source_url"] == "https://math-ege.sdamgia.ru/problem?id=4815"
    assert RECORD["transcription"] == r"90^\circ,\quad\sin A=\frac{3}{5},\quad BC=3"
    assert len(RECORD["source_images"]) == 2
    assert all(
        len(im["svg_sha256"]) == 64 and im["url"].endswith(".svg")
        for im in RECORD["source_images"]
    )
    assert not {"answer", "solution", "expected_answer"} & RECORD.keys()
