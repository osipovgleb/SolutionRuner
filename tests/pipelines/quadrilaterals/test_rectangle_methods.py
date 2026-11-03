"""Exact geometry checks native square/rectangle answers and every proof equality."""

import math
import re
from copy import deepcopy
from fractions import Fraction

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from rectangle_source_cases import CASES, GROUPS, arguments, plan
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.quadrilaterals.parallelogram.rectangle_model import (
    read_question,
)

EXPECTED = dict(
    zip(
        (c["task"] for c in CASES),
        [
            "0,5",
            "722",
            "364,5",
            "200",
            "6",
            "9",
            "13",
            "11",
            "18",
            "84",
            "60",
            "36",
            "14",
            "12",
            "14",
            "14",
            "48",
            "26,5",
            "11,5",
            "24,5",
            "13",
            "3",
            "4",
            "36",
        ],
    )
)


def model(case, context=None):
    ctx = context or case["context"]
    return read_question(
        section(ctx, "condition")["html"], arguments(case["group"])["parent_asset_id"]
    )


def verify(html, m):
    vals = {
        "a": m.a,
        "b": m.b,
        "c": m.diagonal,
        "t": m.a,
        "S": m.area,
        "P": m.perimeter,
        "AC": m.diagonal,
        "BD": m.diagonal,
        "b_1": m.a,
        "b_2": m.b,
        "t_1": m.a,
        "t_2": m.b,
    }
    if m.mode == "ratio":
        vals["a"] = sp.simplify(m.a / m.given[1])
    if m.mode == "difference":
        vals["D"] = m.given[1] ** 2 + 4 * m.given[0]
    elif m.mode in {"side", "diagonal"}:
        vals["D"] = m.given[0] ** 2 / 4 - 4 * m.given[1]
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        statement = node["data-inline-latex"].replace("ab", "a b")
        for label, value in sorted(vals.items(), key=lambda item: -len(item[0])):
            literal = sp.latex(value)
            statement = re.sub(
                r"(?<![A-Za-z_])" + re.escape(label) + r"(?![A-Za-z_])",
                lambda _, literal=literal: "(" + literal + ")",
                statement,
            )
        statement = statement.replace(r"\sqrt{0}", "0")
        for equation in statement.split(r",\quad "):
            values = [
                float(TrigonometricParser(part).parse().value)
                for part in equation.split("=")
            ]
            assert len(values) > 1 and all(
                math.isclose(v, values[0], abs_tol=1e-8, rel_tol=1e-9) for v in values
            ), equation


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_geometry_all_formula_steps_and_parent_remarks(case):
    m, result = model(case), plan(case)
    assert result.answer == EXPECTED[case["task"]]
    saved = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    assert Fraction(saved.replace(",", ".")) == Fraction(
        result.answer.replace(",", ".")
    )
    a, b = float(m.a), float(m.b)
    assert a > 0 and b > 0
    assert float(m.area) == pytest.approx(a * b)
    assert float(m.perimeter) == pytest.approx(2 * (a + b))
    assert float(m.diagonal) == pytest.approx(math.hypot(a, b))
    if m.mode == "square":
        assert a == pytest.approx(b) and float(m.diagonal) == float(m.given[0])
    elif m.mode == "difference":
        assert b - a == pytest.approx(float(m.given[1]))
    elif m.mode == "ratio":
        assert a / b == pytest.approx(float(m.given[1] / m.given[2]))
    else:
        assert float(m.perimeter) == float(m.given[0])
    html = solution_html(result)
    verify(html, m)
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.select("section")) == 1
    assert not soup.find("img")
    if m.mode == "diagonal":
        assert [b.get_text() for b in soup.find_all("b")] == [
            "Примечание 1.",
            "Примечание 2.",
        ]
        assert "Виета" in soup.get_text() and "не решать систему" in soup.get_text()
    else:
        assert not soup.find("b")
        assert 5 <= len(soup.select("center [data-inline-latex]")) <= 9


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_immutable_input_saved_answer_unused_missing_condition_image_restored_and_empty_replay(
    case,
):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    if section(ctx, "solution"):
        section(ctx, "solution")["html"] = "<p>Не использовать: 999.</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == EXPECTED[case["task"]]
    replay(ctx, result.transformations)
    assert len(ctx["normalized_content"]["assets"]) == 1
    assert section(ctx, "source") == section(before, "source")
    old = BeautifulSoup(section(before, "condition")["html"], "html.parser")
    new = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
    if old.img:
        old.img.decompose()
    new.img.decompose()
    assert str(new) == str(old)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_local_frozen_roundtrip_restores_existing_sources_without_upload_and_resumes(
    case,
):
    gw = OfflineGateway(case)
    child = {
        "problem_id": case["context"]["problem_id"],
        "source_problem_id": case["task"],
    }
    rule = GROUPS[case["group"]]["rule"]
    record = _prepared_record(
        gw, child, content_rule_key=rule, **arguments(case["group"])
    )
    assert record["status"] == "prepared", record
    assert not gw.writes and not gw.uploads
    result = _apply_record(
        gw, record, content_rule_key=rule, **arguments(case["group"])
    )
    assert result["status"] == "applied", result
    assert len(gw.writes) == 1 and not gw.uploads
    assert (
        _apply_record(gw, record, content_rule_key=rule, **arguments(case["group"]))[
            "status"
        ]
        == "already_complete"
    )
    assert len(gw.writes) == 1


@pytest.mark.parametrize("group", GROUPS)
def test_registration_requires_actual_reviewed_parent_frozen_manifest_and_readback(
    group,
):
    p, h = get_group_profile(group), get_handler(GROUPS[group]["rule"])
    assert (
        p.source_group_id == GROUPS[group]["group_uuid"]
        and p.existing_solution_policy == "rewrite"
    )
    assert (
        h.parent_from_group_listing
        and h.requires_frozen_manifest
        and h.verify_content_readback
    )
    h.validate()


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "change", ["extra", "missing", "wrong_image", "solution_image"]
)
def test_unreviewed_parent_method_or_figures_blocks_preparation(group, change):
    case = next(c for c in CASES if c["task"] == group)
    kwargs = {}
    if change == "extra":
        kwargs["parent_solution_html"] = (
            arguments(group)["parent_solution_html"] + "<p>Другой метод.</p>"
        )
    elif change == "missing":
        kwargs["parent_solution_html"] = ""
    elif change == "wrong_image":
        kwargs["parent_asset_id"] = "foreign"
    else:
        kwargs["parent_solution_assets"] = ({"asset_key": "image_2"},)
    with pytest.raises(ContentPlanError):
        plan(case, **kwargs)


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "change",
    [
        "instruction",
        "hidden",
        "new_fact",
        "zero",
        "foreign_image",
        "wrong_owner",
        "duplicate",
    ],
)
def test_complete_question_and_image_ownership_validation_fail_closed(group, change):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    condition = section(ctx, "condition")
    if change == "instruction":
        condition["html"] += "<p>Округлите до целых.</p>"
    elif change == "hidden":
        condition["html"] += '<p hidden="">Новые данные.</p>'
    elif change == "new_fact":
        condition["html"] += "<p>AB = 7.</p>"
    elif change == "zero":
        soup = BeautifulSoup(condition["html"], "html.parser")
        soup.img.extract()
        plain = str(soup)
        condition["html"] = re.sub(r"\d+", "0", plain)
        condition["asset_keys"] = []
        ctx["normalized_content"]["assets"] = []
    elif change == "foreign_image":
        ctx["normalized_content"]["assets"][0]["asset_id"] = "foreign"
    elif change == "wrong_owner":
        condition["asset_keys"] = []
    else:
        ctx["normalized_content"]["sections"].append(deepcopy(condition))
    with pytest.raises((ContentPlanError, ValueError)):
        plan(case, ctx)


@pytest.mark.parametrize(
    "group,question,expected",
    [
        ("27582", "Найдите площадь квадрата, если его диагональ равна 1,5.", "1,125"),
        (
            "27601",
            "Площадь прямоугольника равна 6. Найдите его большую сторону, если она на 1 больше меньшей стороны.",
            "3",
        ),
        (
            "27603",
            "Найдите периметр прямоугольника, если его площадь равна 2, а отношение соседних сторон равно 2 : 1.",
            "6",
        ),
        (
            "27603",
            "Найдите периметр прямоугольника, если его площадь равна 1, а отношение соседних сторон равно 1 : 2.",
            r"3 \sqrt{2}",
        ),
        (
            "27604",
            "Периметр прямоугольника равен 12, а площадь 6. Найдите большую сторону прямоугольника.",
            r"\sqrt{3} + 3",
        ),
        (
            "27604",
            "Периметр прямоугольника равен 8, а площадь 4. Найдите большую сторону прямоугольника.",
            "2",
        ),
        (
            "27605",
            "Периметр прямоугольника равен 8, а диагональ равна 3. Найдите площадь этого прямоугольника.",
            "3,5",
        ),
        (
            "27606",
            "Периметр прямоугольника равен 12, а площадь равна 6. Найдите диагональ этого прямоугольника.",
            r"2 \sqrt{6}",
        ),
    ],
)
def test_exact_decimals_algebraic_answers_equal_sides_and_reverse_ratio(
    group, question, expected
):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    image = str(BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img)
    section(ctx, "condition")["html"] = image + "<p>" + question + "</p>"
    initial = deepcopy(ctx)
    m, result = model(case, ctx), plan(case, ctx)
    assert (
        sp.simplify(
            TrigonometricParser(result.answer).parse().value
            - TrigonometricParser(expected).parse().value
        )
        == 0
    )
    verify(solution_html(result), m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    if "\\" in result.answer:
        assert (
            BeautifulSoup(section(ctx, "answer")["html"], "html.parser").find("span")[
                "data-inline-latex"
            ]
            == result.answer
        )
        gw = OfflineGateway({"context": initial})
        rule = GROUPS[group]["rule"]
        record = _prepared_record(
            gw,
            {"problem_id": initial["problem_id"], "source_problem_id": case["task"]},
            content_rule_key=rule,
            **arguments(group),
        )
        assert record["status"] == "prepared", record
        applied = _apply_record(gw, record, content_rule_key=rule, **arguments(group))
        assert applied["status"] == "applied", applied
        assert not gw.uploads and len(gw.writes) == 1
        assert (
            _apply_record(gw, record, content_rule_key=rule, **arguments(group))[
                "status"
            ]
            == "already_complete"
        )


@pytest.mark.parametrize(
    "question",
    [
        "Периметр прямоугольника равен 10, а площадь 7. Найдите большую сторону прямоугольника.",
        "Периметр прямоугольника равен 10, а площадь равна 7. Найдите диагональ этого прямоугольника.",
        "Периметр прямоугольника равен 10, а диагональ равна 2. Найдите площадь этого прямоугольника.",
        "Периметр прямоугольника равен 10, а диагональ равна 5. Найдите площадь этого прямоугольника.",
        "Периметр прямоугольника равен 10, а диагональ равна 6. Найдите площадь этого прямоугольника.",
        "Найдите площадь квадрата, если его диагональ равна -1.",
        "Площадь прямоугольника равна 1. Найдите его большую сторону, если она на 0 больше меньшей стороны.",
        "Найдите периметр прямоугольника, если его площадь равна 1, а отношение соседних сторон равно 1 : 0.",
    ],
)
def test_geometrically_impossible_or_nonpositive_data_fail_closed(question):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + question + "</p>")


@pytest.mark.parametrize(
    "task,omitted", [("54805", "asset:image_1"), ("55757", "section:condition:1")]
)
def test_missing_restored_condition_readback_is_reported_as_failure(task, omitted):
    case = next(c for c in CASES if c["task"] == task)
    gw = OfflineGateway(case, omit=omitted)
    rule = GROUPS[case["group"]]["rule"]
    record = _prepared_record(
        gw,
        {"problem_id": case["context"]["problem_id"], "source_problem_id": task},
        content_rule_key=rule,
        **arguments(case["group"]),
    )
    result = _apply_record(
        gw, record, content_rule_key=rule, **arguments(case["group"])
    )
    assert result["status"] == "failed", result
