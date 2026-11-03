"""Cyclic trapezoid boundaries, method placement and both static image roles."""

from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from circumcircle_source_cases import CASES, plan, read
from midpoint_source_cases import section, solution_html
from test_circumcircle_lifecycle import apply_offline, prepared, remove_images
from test_circumcircle_methods import verify
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.circles.circumcircle_model import read_question
from solution_runner.pipelines.core.errors import ContentPlanError


def leg_condition(perimeter, midline):
    return f"<p>Около трапеции описана окружность. Периметр трапеции равен {perimeter}, средняя линия равна {midline}. Найдите боковую сторону трапеции.</p>"


def radius_condition(angle, base):
    return f"<p>Боковая сторона равнобедренной трапеции равна ее меньшему основанию, угол при основании равен {angle}°, большее основание равно {base}. Найдите радиус описанной окружности этой трапеции.</p>"


@pytest.mark.parametrize("perimeter,midline", [(4, 2), (3, 2), (0, 2), (4, 0)])
def test_impossible_or_degenerate_trapezoid_values_fail_closed(perimeter, midline):
    with pytest.raises(ContentPlanError):
        read_question(leg_condition(perimeter, midline))


@pytest.mark.parametrize("angle,base", [(59, 12), (120, 12), (0, 12), (60, 0)])
def test_another_angle_or_nonpositive_base_cannot_use_sixty_degree_methods(angle, base):
    with pytest.raises(ContentPlanError):
        read_question(radius_condition(angle, base))


@pytest.mark.parametrize("html", [leg_condition(22, 5), radius_condition(60, 12)])
def test_unknown_instructions_and_incircle_replacement_fail_closed(html):
    for changed in [
        html + "<p>Округлите ответ.</p>",
        html.replace("описана", "вписана").replace("описанной", "вписанной"),
    ]:
        with pytest.raises(ContentPlanError):
            read_question(changed)


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] == "27925"], ids=lambda c: c["task"]
)
def test_projection_picture_stays_first_and_other_two_methods_have_no_copies(case):
    soup = BeautifulSoup(solution_html(plan(case)), "html.parser")
    first, second, third = soup.select("section")
    assert first.find(["p", "center"]).find("img")
    assert not second.find("img") and not third.find("img")
    assert first.find("img")["data-asset-id"] == "fc89bc2b-18eb-447d-9299-1639f467c25e"
    assert "Хорды AD, DC и CB равны" in second.get_text()
    assert r"30^{circ}" not in str(third)


@pytest.mark.parametrize(
    "prefix",
    ["asset:image_1", "asset:image_2", "section:condition", "section:solution"],
)
def test_missing_static_trapezoid_role_readback_is_failure(prefix):
    case = next(c for c in CASES if c["task"] == "27925")
    gateway = OfflineGateway(case)
    remove_images(gateway)
    record = prepared(case, gateway)
    assert record["status"] == "prepared"
    gateway.omit = next(
        t["transformation_target_id"]
        for t in record["transformations"]
        if t["transformation_target_id"].startswith(prefix)
    )
    assert apply_offline(case, gateway, record)["status"] == "failed"
    assert not gateway.uploads


@pytest.mark.parametrize("group", ["27924", "27925"])
def test_composite_positive_values_keep_every_equality_correct(group):
    case = next(c for c in CASES if c["task"] == group)
    context = deepcopy(case["context"])
    condition = section(context, "condition")
    image = str(BeautifulSoup(condition["html"], "html.parser").find("img"))
    if group == "27924":
        html = leg_condition(
            r'<span data-inline-latex="8+4\sqrt{2}"></span>',
            r'<span data-inline-latex="2+\sqrt{2}"></span>',
        )
        expected = 2 + sp.sqrt(2)
    else:
        html = radius_condition(60, r'<span data-inline-latex="6+2\sqrt{2}"></span>')
        expected = 3 + sp.sqrt(2)
    condition["html"] = image + html
    result = plan(case, context)
    model = read(context)
    assert sp.simplify(model.answer - expected) == 0
    verify(solution_html(result), model)
