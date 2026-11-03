"""Sine topology, strict angle guards and complete hexagon figure readback."""

from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from circumcircle_quantity_cases import SINES
from circumcircle_source_cases import CASES, plan, read
from midpoint_source_cases import replay, section, solution_html
from test_circumcircle_lifecycle import apply_offline, prepared, remove_images
from test_circumcircle_methods import verify
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.errors import ContentPlanError


def query_context(case, html):
    context = deepcopy(case["context"])
    condition = section(context, "condition")
    image = BeautifulSoup(condition["html"], "html.parser").find("img")
    condition["html"] = "<p>" + str(image) + html + "</p>"
    return context


@pytest.mark.parametrize("angle", SINES)
@pytest.mark.parametrize("group", ["27918", "27921", "27920"])
def test_standard_angles_share_sine_math_and_choose_the_correct_triangle_type(
    group, angle
):
    case = next(c for c in CASES if c["task"] == group)
    html = (
        f"Угол C треугольника ABC, вписанного в окружность радиуса 6, равен {angle}°. Найдите сторону AB этого треугольника."
        if group == "27920"
        else f"Сторона AB треугольника ABC равна 6. Противолежащий ей угол C равен {angle}°. Найдите радиус окружности, описанной около этого треугольника."
    )
    context = query_context(case, html)
    result = plan(case, context)
    expected = 12 * SINES[angle] if group == "27920" else 3 / SINES[angle]
    assert sp.simplify(read(context).answer - expected) == 0
    verify(solution_html(result), read(context))
    replay(context, result.transformations)
    source = context["normalized_content"]["assets"][0]["asset_id"]
    allowed = (
        ("f0cf673f-8658-42ed-a2e3-58b4debfd315", "76a7c802-b4a8-4880-af3c-e4e7855a95f9")
        if angle < 90
        else ("a124add8-430b-4761-ad72-2f022dc85c73",)
        if angle == 90
        else (
            "0676249d-0639-4ff4-9c2b-bdfacc3f5390",
            "8498fd3b-9859-41b8-b9fc-df1e9c030e93",
            "e5506a55-6c96-4c42-b5bd-b826625e6e4f",
        )
    )
    assert source in allowed
    assert plan(case, context).transformations == ()


BAD = (
    (
        "27918",
        "Сторона AB треугольника ABC равна 6. Противолежащий ей угол C равен 0°. Найдите радиус окружности, описанной около этого треугольника.",
    ),
    (
        "27918",
        "Сторона AB треугольника ABC равна 6. Противолежащий ей угол C равен 180°. Найдите радиус окружности, описанной около этого треугольника.",
    ),
    (
        "27918",
        "Сторона AB треугольника ABC равна 6. Противолежащий ей угол C равен 20°. Найдите радиус окружности, описанной около этого треугольника.",
    ),
    (
        "27898",
        "В треугольнике ABC AC = 4, BC = 3, угол C равен 60°. Найдите радиус описанной окружности этого треугольника.",
    ),
    (
        "27898",
        "В треугольнике ABC угол C равен 60°, AC = 4, BC = 3. Найдите радиус описанной окружности этого треугольника.",
    ),
    (
        "27900",
        "Боковая сторона равнобедренного треугольника равна 1, угол при вершине, противолежащей основанию, равен 90°. Найдите диаметр описанной окружности этого треугольника.",
    ),
    (
        "27906",
        "Чему равна сторона правильного шестиугольника, вписанного в окружность, радиус которой равен 0?",
    ),
)


@pytest.mark.parametrize("group,html", BAD)
def test_unsupported_angles_and_degenerate_data_block_before_any_local_write(
    group, html
):
    case = next(c for c in CASES if c["task"] == group)
    context = query_context(case, html)
    with pytest.raises(ContentPlanError):
        plan(case, context)
    gateway = OfflineGateway({**case, "context": context})
    assert prepared(case, gateway)["status"] == "blocked"
    assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize(
    "prefix",
    ["asset:image_1", "asset:image_2", "section:condition", "section:solution"],
)
def test_hexagon_equilateral_picture_and_sections_require_readback(prefix):
    case = next(c for c in CASES if c["task"] == "27906")
    gateway = OfflineGateway(case)
    remove_images(gateway)
    record = prepared(case, gateway)
    gateway.omit = next(
        t["transformation_target_id"]
        for t in record["transformations"]
        if t["transformation_target_id"].startswith(prefix)
    )
    assert apply_offline(case, gateway, record)["status"] == "failed"
    assert not gateway.uploads


@pytest.mark.parametrize("drift", ["condition", "answer", "asset"])
def test_wrong_original_acute_picture_is_repaired_but_frozen_drift_cannot_write(drift):
    case = next(c for c in CASES if c["task"] == "516291")
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    assert record["status"] == "prepared" and record["expected_answer"] == "37"
    assert (
        gateway.context["normalized_content"]["assets"][0]["asset_id"]
        == "76a7c802-b4a8-4880-af3c-e4e7855a95f9"
    )
    if drift == "asset":
        gateway.context["normalized_content"]["assets"][0]["asset_id"] = "foreign"
    else:
        section(gateway.context, drift)["html"] += "<p>Иные данные</p>"
    assert apply_offline(case, gateway, record)["status"] in {"blocked", "failed"}
    assert not gateway.uploads and not gateway.writes
