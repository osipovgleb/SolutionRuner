"""Check all native chord/tangent answers and every equality in every parent method."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from tangent_source_cases import CASES, GROUPS, arguments, plan, read

from solution_runner.pipelines.circles.quantity_parent import FAMILIES
from solution_runner.pipelines.circles.quantity_sources import PARENTS
from solution_runner.pipelines.circles.tangent_model import read_question
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser

ARC = r"\overset{\frown}{AB}"
FAR = r"\overset{\frown}{AD}"
TITLES = {
    "chord_obtuse": ["Решение", "Приведём другое решение"],
    "two_tangents_arc": [
        "Решение",
        "Приведем другое решение",
        "Альтернативное решение.",
    ],
    "far_angle": ["Решение", "Альтернативное решение."],
    "far_arc": ["Решение", "Приведём другое решение"],
}


def variables(m):
    a = m.given[0]
    if m.mode.startswith("chord_"):
        radius = m.given[1]
        central = 2 * min(a, 180 - a)
        return {
            "R": radius,
            "AO": radius,
            "OC": radius,
            "AC": 2 * radius * sp.sin(sp.pi * a / 180),
            r"\angle ABC": a,
            r"\angle AOC": central,
            r"\angle OAC": (180 - central) / 2,
            r"\angle OCA": (180 - central) / 2,
            r"\sin120^{\circ}": sp.sqrt(3) / 2,
            r"\cos120^{\circ}": -sp.Rational(1, 2),
            r"\sin\angle ABC": sp.sin(sp.pi * a / 180),
            r"\cos\angle AOC": sp.cos(sp.pi * central / 180),
        }
    if m.mode == "arc_ratio":
        unit = 360 / sum(m.given)
        return {
            "x": unit,
            r"\beta": max(m.given) * unit,
            r"\angle ACB": max(m.given) * unit / 2,
        }
    if m.mode == "tangent_chord":
        return {r"\theta": a, r"\angle ABC": a / 2}
    if m.mode == "central_from_tangent":
        return {ARC: 2 * a, r"\angle CAB": a, r"\angle AOB": 2 * a}
    if m.mode == "two_tangents_angle":
        return {
            ARC: a,
            r"\angle CAB": a / 2,
            r"\angle CBA": a / 2,
            r"\angle ACB": 180 - a,
        }
    if m.mode == "two_tangents_arc":
        return {
            "CA": 1,
            "CB": 1,
            ARC: 180 - a,
            "x": 180 - a,
            r"\angle BAC": (180 - a) / 2,
            r"\angle ACB": a,
            r"\angle AOB": 180 - a,
            r"\angle OAC": 90,
            r"\angle OBC": 90,
        }
    if m.mode in {"near_angle", "near_arc"}:
        arc = a if m.mode == "near_angle" else 90 - a
        return {
            ARC: arc,
            r"\angle AOC": arc,
            r"\angle ACO": 90 - arc,
            r"\angle OAC": 90,
        }
    far = a if m.mode == "far_angle" else 90 + a
    return {
        FAR: far,
        ARC: 180 - far,
        "x": far,
        r"\angle AOD": far,
        r"\angle DOA": far,
        r"\angle AOB": 180 - far,
        r"\angle ACO": far - 90,
        r"\angle OAC": 90,
    }


def verify(html, model):
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        for label, amount in sorted(variables(model).items(), key=lambda x: -len(x[0])):
            formula = re.sub(
                (r"" if label.startswith("\\") else r"(?<![A-Za-z_])")
                + re.escape(label)
                + r"(?![A-Za-z_])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                formula,
            )
        formula = formula.replace(r"^{\circ}", "")
        amounts = [
            TrigonometricParser(expr).parse().value for expr in formula.split("=")
        ]
        assert len(amounts) > 1, formula
        assert all(sp.simplify(v - amounts[0]) == 0 for v in amounts), formula


def test_one_preparer_covers_exactly_all_pinned_circle_parent_rules():
    assert set(FAMILIES) == set(PARENTS)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_each_equality_and_all_parent_methods(case):
    model, result = read(case["context"]), plan(case)
    saved = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    expected = "58" if case["task"] == "52119" else saved
    assert sp.Rational(result.answer.replace(",", ".")) == sp.Rational(
        expected.replace(",", ".")
    )
    html = solution_html(result)
    verify(html, model)
    soup = BeautifulSoup(html, "html.parser")
    assert [s["data-solution-title"] for s in soup.select("section")] == TITLES.get(
        model.mode, ["Решение"]
    )
    assert len(soup.find_all("img")) == (
        1
        if model.mode in {"chord_thirty", "chord_obtuse", "central_from_tangent"}
        else 0
    )
    assert (
        "Ранее это задание" not in soup.get_text()
        and "Примечание об изменении" not in soup.get_text()
    )
    if model.mode == "chord_thirty":
        assert "равносторонний" in soup.get_text()
    if model.mode == "chord_obtuse":
        assert "косинусов" in soup.get_text() and "синусов" in soup.get_text()
    if model.mode == "two_tangents_arc":
        assert "четырёхугольника" in soup.get_text()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_immutable_sources_saved_answer_unused_and_empty_replay(case):
    context = deepcopy(case["context"])
    section(context, "answer")["html"] = "<p>999</p>"
    before = deepcopy(context)
    result = plan(case, context)
    assert context == before and result.answer == plan(case).answer
    replay(context, result.transformations)
    assert plan(case, context).transformations == ()
    assert section(context, "condition") == section(before, "condition")
    assert section(context, "source") == section(before, "source")


@pytest.mark.parametrize("group", GROUPS.values(), ids=lambda g: g["key"])
@pytest.mark.parametrize("change", ["html", "primary", "assets"])
def test_profiles_and_complete_parent_pins_fail_closed(group, change):
    profile, handler = get_group_profile(group["key"]), get_handler(group["rule"])
    assert (
        profile.source_group_id == group["group_uuid"]
        and profile.existing_solution_policy == "rewrite"
    )
    assert (
        handler.parent_from_group_listing
        and handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )
    handler.validate()
    args = arguments(group["key"])
    override = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Иной метод</p>"}
        if change == "html"
        else {"parent_asset_id": "foreign"}
        if change == "primary"
        else {
            "parent_solution_assets": (
                {
                    "asset_key": "image_9",
                    "source_asset_id": "foreign",
                    "url": "/assets/foreign",
                },
            )
        }
    )
    case = next(c for c in CASES if c["task"] == group["key"])
    with pytest.raises(ContentPlanError):
        plan(case, **override)


@pytest.mark.parametrize(
    "html,expected",
    [
        (
            "Хорда AB делит окружность на две части, градусные величины которых относятся как 7 : 5. Под каким углом видна эта хорда из точки C, принадлежащей меньшей дуге окружности? Ответ дайте в градусах.",
            105,
        ),
        (
            "Угол ACO равен 12,5°, где O — центр окружности. Его сторона CA касается окружности. Найдите величину меньшей дуги AB окружности, заключенной внутри этого угла. Ответ дайте в градусах.",
            sp.Rational(155, 2),
        ),
    ],
)
def test_reversed_ratio_and_decimal_angles_are_exact(html, expected):
    assert read_question("<p>" + html + "</p>").answer == expected


@pytest.mark.parametrize(
    "html",
    [
        "Найдите хорду, на которую опирается угол 45°, вписанный в окружность радиуса 3.",
        "Найдите хорду, на которую опирается угол 30°, вписанный в окружность радиуса 0.",
        "Хорда AB делит окружность на две части, градусные величины которых относятся как 5 : 5. Под каким углом видна эта хорда из точки C, принадлежащей меньшей дуге окружности? Ответ дайте в градусах.",
        "Хорда AB стягивает дугу окружности в 180°. Найдите угол ABC между этой хордой и касательной к окружности, проведенной через точку B. Ответ дайте в градусах.",
        "Через концы A и B дуги окружности с центром O проведены касательные AC и BC. Угол CAB равен 90°. Найдите угол AOB. Ответ дайте в градусах.",
        "Касательные CA и CB к окружности образуют угол ACB, равный 180°. Найдите величину меньшей дуги AB, стягиваемой точками касания. Ответ дайте в градусах.",
        "Угол ACO равен 90°, где O — центр окружности. Его сторона CA касается окружности. Найдите величину меньшей дуги AB окружности, заключенной внутри этого угла. Ответ дайте в градусах.",
        "Найдите угол ACO, если его сторона CA касается окружности, O — центр окружности, а большая дуга AD окружности, заключенная внутри этого угла, равна 80°. Ответ дайте в градусах.",
        "Найдите хорду, на которую опирается угол 30°, вписанный в окружность радиуса 3. Округлите ответ.",
    ],
)
def test_degenerate_and_unreviewed_questions_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + html + "</p>")
