"""Cyclic angle existence, unnamed-angle ambiguity and legacy-detail ownership."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from circle_angle_source_cases import CASES, plan
from midpoint_source_cases import replay, section
from test_circle_angle_lifecycle import apply_offline, prepared
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.circles.angle_model import read_question
from solution_runner.pipelines.core.errors import ContentPlanError

BAD = (
    (
        "27927",
        "Два угла вписанного в окружность четырехугольника равны 40° и 140°. Найдите больший из оставшихся углов. Ответ дайте в градусах.",
    ),
    (
        "27927",
        "Два угла вписанного в окружность четырехугольника равны 90° и 90°. Найдите больший из оставшихся углов. Ответ дайте в градусах.",
    ),
    (
        "27871",
        "Угол A четырехугольника ABCD, вписанного в окружность, равен 180°. Найдите угол C этого четырехугольника. Ответ дайте в градусах.",
    ),
    (
        "27872",
        "Стороны четырехугольника ABCD AB, BC, CD и AD стягивают дуги описанной окружности, градусные величины которых равны соответственно 30°, 40°, 50°, 239°. Найдите угол B этого четырехугольника. Ответ дайте в градусах.",
    ),
    (
        "27875",
        "Четырехугольник ABCD вписан в окружность. Угол ABD равен 100°, угол CAD равен 80°. Найдите угол ABC. Ответ дайте в градусах.",
    ),
    (
        "27876",
        "Четырехугольник ABCD вписан в окружность. Угол ABC равен 40°, угол ABD равен 40°. Найдите угол CAD. Ответ дайте в градусах.",
    ),
    (
        "27876",
        "Четырехугольник ABCD вписан в окружность. Угол ABC равен 40°, угол ABD равен 60°. Найдите угол CAD. Ответ дайте в градусах.",
    ),
    (
        "27868",
        "Точки A, B, C, расположенные на окружности, делят ее на три дуги, градусные величины которых относятся как 1:0:5. Найдите больший угол треугольника ABC. Ответ дайте в градусах.",
    ),
)


@pytest.mark.parametrize("group,html", BAD)
def test_impossible_or_underdetermined_angles_block_before_any_local_write(group, html):
    case = next(c for c in CASES if c["task"] == group)
    context = deepcopy(case["context"])
    sec = section(context, "condition")
    image = BeautifulSoup(sec["html"], "html.parser").find("img")
    sec["html"] = "<p>" + str(image) + html + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, context)
    gateway = OfflineGateway({**case, "context": context})
    assert prepared(case, gateway)["status"] == "blocked"
    assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize("ratio", ["2:3:4", "4:2:3", r"3\colon4\colon2"])
def test_largest_triangle_angle_does_not_depend_on_ratio_order(ratio):
    html = (
        "Точки A, B, C, расположенные на окружности, делят ее на три дуги, градусные величины которых относятся как "
        + ratio
        + ". Найдите больший угол треугольника ABC. Ответ дайте в градусах."
    )
    assert read_question("<p>" + html + "</p>").answer == 80


def test_one_consecutive_arc_may_exceed_a_semicircle():
    html = "Стороны четырехугольника ABCD AB, BC, CD и AD стягивают дуги описанной окружности, градусные величины которых равны соответственно 30°, 40°, 50°, 240°. Найдите угол B этого четырехугольника. Ответ дайте в градусах."
    assert read_question("<p>" + html + "</p>").answer == 145


def test_unused_ratio_solution_picture_is_removed_and_primary_source_is_preserved():
    case = next(c for c in CASES if c["task"] == "51383")
    before = deepcopy(case["context"])
    context = deepcopy(before)
    result = plan(case, context)
    assert context == before
    replay(context, result.transformations)
    assert section(context, "condition") == section(before, "condition")
    assert len(context["normalized_content"]["assets"]) == 1
    assert (
        context["normalized_content"]["assets"][0]
        == before["normalized_content"]["assets"][0]
    )
    assert section(context, "solution")["asset_keys"] == []
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize("change", ["id", "owner", "duplicate"])
def test_legacy_ratio_cleanup_does_not_allow_foreign_or_misowned_images(change):
    case = next(c for c in CASES if c["task"] == "51383")
    context = deepcopy(case["context"])
    solution = section(context, "solution")
    soup = BeautifulSoup(solution["html"], "html.parser")
    image = soup.find("img")
    if change == "id":
        asset = context["normalized_content"]["assets"][1]
        old, new = (
            asset["asset_id"],
            context["normalized_content"]["assets"][0]["asset_id"],
        )
        asset["asset_id"], asset["url"] = new, "/assets/" + new
        solution["html"] = solution["html"].replace(old, new)
    elif change == "duplicate":
        soup.append(deepcopy(image))
        solution["html"] = str(soup)
    else:
        image.extract()
        solution["html"] = str(soup)
        solution["asset_keys"] = []
        answer = section(context, "answer")
        answer["html"] += str(image)
        answer["asset_keys"] = ["image_2"]
    with pytest.raises(ContentPlanError):
        plan(case, context)


@pytest.mark.parametrize("drift", ["condition", "answer", "asset"])
def test_wrong_saved_answer_one_is_corrected_but_frozen_changes_cannot_write(drift):
    case = next(c for c in CASES if c["task"] == "51685")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and record["expected_answer"] == "25"
    if drift == "asset":
        gateway.context["normalized_content"]["assets"][0]["asset_id"] = "foreign"
    else:
        section(gateway.context, drift)["html"] += "<p>Иные данные</p>"
    assert apply_offline(case, gateway, record)["status"] in {"blocked", "failed"}
    assert not gateway.uploads and not gateway.writes
