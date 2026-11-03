"""Check every native bisector method, equality, answer, refusal and replay."""

import itertools
import math
import re
from copy import deepcopy

import pytest
import sympy as sp
from bisector_source_cases import CASES, GROUPS, arguments, plan
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from test_parallelogram_quantity_model import read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.quadrilaterals.parallelogram.quantity_model import (
    read_question,
)


def geometric_angle(p, name):
    first, vertex, last = (p[n] for n in name)
    u = first[0] - vertex[0], first[1] - vertex[1]
    v = last[0] - vertex[0], last[1] - vertex[1]
    cosine = sum(u[i] * v[i] for i in (0, 1)) / (math.hypot(*u) * math.hypot(*v))
    return math.degrees(math.acos(max(-1, min(1, cosine))))


def variables(m):
    if m.mode == "rhombus_angle":
        a, b = 1, 1
        cosine, sine = (
            math.cos(math.radians(float(m.angle_a))),
            math.sin(math.radians(float(m.angle_a))),
        )
    else:
        a, b = map(float, (m.first, m.second))
        cosine, sine = 0.37, math.sqrt(1 - 0.37**2)
    p = {
        "A": (0, 0),
        "B": (a * cosine, -a * sine),
        "C": (b + a * cosine, -a * sine),
        "D": (b, 0),
    }
    values = {}
    if m.mode == "bisector_ratio":
        p["L"] = (a, 0)
        r, s, perimeter = m.given
        values.update(x=perimeter / (2 * (2 * r + s)), P=perimeter)
    elif m.mode == "bisector_double":
        p["E"] = (a, 0)
    else:
        for vertex, name in {"A": "DAB", "B": "ABC", "C": "BCD", "D": "CDA"}.items():
            values[r"\angle " + vertex] = geometric_angle(p, name)
    for name in itertools.permutations(p, 3):
        values[r"\angle " + "".join(name)] = geometric_angle(p, name)
    for name in itertools.permutations(p, 2):
        values["".join(name)] = math.dist(p[name[0]], p[name[1]])
    return values


def verify(html, m):
    values = variables(m)
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        for label, value in sorted(values.items(), key=lambda row: -len(row[0])):
            literal = (
                "("
                + sp.latex(
                    sp.Rational(str(round(value, 6)))
                    if isinstance(value, float)
                    else value
                )
                + ")"
            )
            if label.startswith("\\angle"):
                formula = formula.replace(label, literal)
            else:
                formula = re.sub(
                    r"(?<![A-Za-z_])" + re.escape(label) + r"(?![A-Za-z_])",
                    lambda _, v=literal: v,
                    formula,
                )
        formula = formula.replace(r"^{\circ}", "")
        for statement in re.split(r",\s*\\quad\s*", formula):
            numbers = [
                float(TrigonometricParser(v).parse().value)
                for v in statement.split("=")
            ]
            assert len(numbers) > 1, statement
            assert all(
                math.isclose(v, numbers[0], rel_tol=1e-9, abs_tol=1e-6) for v in numbers
            ), statement


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_all_formulas_unchanged_inputs_and_replay(case):
    ctx = deepcopy(case["context"])
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before
    expected = case.get(
        "expected_answer",
        BeautifulSoup(section(ctx, "answer")["html"], "html.parser").get_text(
            strip=True
        ),
    )
    assert float(result.answer.replace(",", ".")) == float(expected.replace(",", "."))
    verify(solution_html(result), read(ctx))
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    conditions = []
    for context in (ctx, before):
        soup = BeautifulSoup(section(context, "condition")["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        conditions.append(str(soup))
    assert conditions[0] == conditions[1]
    section(ctx, "answer")["html"] = "<p>999</p>"
    assert plan(case, ctx).answer == result.answer


@pytest.mark.parametrize("g", GROUPS.values(), ids=lambda g: g["key"])
@pytest.mark.parametrize("change", ["method", "source", "figures"])
def test_bindings_pin_full_parent_html_and_solution_assets(g, change):
    profile, handler = get_group_profile(g["key"]), get_handler(g["rule"])
    assert (
        profile.source_group_id == g["group_uuid"]
        and profile.existing_solution_policy == "rewrite"
    )
    assert (
        handler.parent_from_group_listing
        and handler.requires_frozen_manifest
        and handler.verify_content_readback
        and handler.strict_frozen_input
    )
    handler.validate()
    case = next(c for c in CASES if c["task"] == g["key"])
    overrides = (
        {
            "parent_solution_html": arguments(g["key"])["parent_solution_html"]
            + "<p>Иной метод.</p>"
        }
        if change == "method"
        else (
            {"parent_asset_id": "foreign"}
            if change == "source"
            else {"parent_solution_assets": ({"asset_key": "foreign"},)}
        )
    )
    with pytest.raises(ContentPlanError):
        plan(case, **overrides)


@pytest.mark.parametrize(
    "html",
    [
        "В ромбе ABCD угол ABC равен 180°. Найдите угол ACD. Ответ дайте в градусах.",
        "В ромбе ABCD угол DBA равен 90°. Найдите угол BCD. Ответ дайте в градусах.",
        "В ромбе ABCD угол AAA равен 10°. Найдите угол BCD. Ответ дайте в градусах.",
        "В ромбе ABCD угол ABC равен 122°. Найдите угол AAA. Ответ дайте в градусах.",
        "В ромбе ABCD угол ABC равен -10°. Найдите угол ACD. Ответ дайте в градусах.",
        "В ромбе ABCD угол ABC равен 122°. Найдите угол ACD. Ответ дайте в градусах. Округлите ответ.",
        "Биссектриса тупого угла параллелограмма делит противоположную сторону в отношении 0:3, считая от вершины острого угла. Найдите большую сторону параллелограмма, если его периметр равен 88.",
        "Биссектриса тупого угла параллелограмма делит противоположную сторону в отношении 4:3, считая от вершины тупого угла. Найдите большую сторону параллелограмма, если его периметр равен 88.",
        "Точка пересечения биссектрис двух углов параллелограмма, прилежащих к одной стороне, принадлежит противоположной стороне. Меньшая сторона параллелограмма равна 0. Найдите его большую сторону.",
    ],
)
def test_invalid_or_unreviewed_questions_fail_closed(html):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + html + "</p>")


@pytest.mark.parametrize(
    "known,amount,target,answer",
    [
        ("ABC", 122, "ACD", 29),
        ("DAB", 136, "BDC", 22),
        ("DBA", 13, "BCD", 154),
        ("CAB", 82, "CDA", 16),
        ("DBA", 88, "BCD", 4),
        ("CAB", 30, "BDC", 60),
        ("DAB", 90, "CBD", 45),
        ("BAC", 30, "DCA", 30),
        ("ABC", 120, "CDA", 120),
    ],
)
def test_full_half_adjacent_opposite_and_reversed_rays(known, amount, target, answer):
    model = read_question(
        f"<p>В ромбе ABCD угол {known} равен {amount}°. Найдите угол {target}. Ответ дайте в градусах.</p>"
    )
    assert model.answer == answer


def test_283357_saved_zero_is_not_used_and_prepared_answer_is_four():
    case = next(c for c in CASES if c["task"] == "283357")
    assert (
        BeautifulSoup(
            section(case["context"], "answer")["html"], "html.parser"
        ).get_text(strip=True)
        == "000"
    )
    assert plan(case).answer == "4"
