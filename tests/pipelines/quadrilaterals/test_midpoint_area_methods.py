"""Independent affine geometry checks every area and every equality in all methods."""

import math
import re
from copy import deepcopy
from fractions import Fraction
from itertools import permutations

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import (
    CASES,
    GROUPS,
    generated,
    plan,
    replay,
    section,
    solution_html,
)

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.quadrilaterals.parallelogram.midpoint_model import (
    FRAMES,
    read_question,
)

AREAS = dict(
    zip(
        (c["task"] for c in CASES),
        [189, 123, 20, 36, 153, 14, 116, 156, 176, 155, 117, 96, 24, 12, 70, 28],
    )
)


def polygon(points):
    return (
        abs(
            sum(
                p[0] * q[1] - p[1] * q[0]
                for p, q in zip(points, points[1:] + points[:1])
            )
        )
        / 2
    )


def coordinates(m, shear=2):
    h = m.given / 8
    canonical = {"A": (0, 0), "B": (shear, h), "C": (8 + shear, h), "D": (8, 0)}
    points = {m.name(k): v for k, v in canonical.items()}
    if m.mode == "varignon":
        for name, edge in zip(("A'", "B'", "C'", "D'"), ("AD", "AB", "BC", "CD")):
            points[name] = tuple(
                (points[edge[0]][i] + points[edge[1]][i]) / sp.Integer(2)
                for i in range(2)
            )
    else:
        edge = m.midpoint
        points["E"] = tuple(
            (points[edge[0]][i] + points[edge[1]][i]) / sp.Integer(2) for i in range(2)
        )
        if m.mode == "triangle":
            a, d, c = [points[m.name(k)] for k in "ADC"]
            u = (c[0] - d[0], c[1] - d[1])
            t = sum((a[i] - d[i]) * u[i] for i in range(2)) / sum(v * v for v in u)
            points["H"] = tuple(d[i] + t * u[i] for i in range(2))
    return points


def geometric_area(points, name):
    return polygon([points[n] for n in re.findall(r"[ABCDEH]'?", name)])


def verify_formulas(html, m):
    points = coordinates(m)
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        formula = re.sub(
            r"S_\{([ABCDEH']+)\}",
            lambda v: "(" + sp.latex(geometric_area(points, v[1])) + ")",
            formula,
        )
        formula = re.sub(
            r"\b[ABCDEH]{2}\b",
            lambda v: (
                "("
                + sp.latex(
                    sp.sqrt(
                        sum(
                            (points[v[0][0]][i] - points[v[0][1]][i]) ** 2
                            for i in range(2)
                        )
                    )
                )
                + ")"
            ),
            formula,
        )
        if m.mode == "trapezoid":
            base = sp.sqrt(
                sum(
                    (points[m.midpoint[0]][i] - points[m.midpoint[1]][i]) ** 2
                    for i in range(2)
                )
            )
            formula = formula.replace("h", "(" + sp.latex(m.given / base) + ")")
        values = [
            float(TrigonometricParser(p).parse().value) for p in formula.split("=")
        ]
        assert len(values) > 1 and all(
            math.isclose(v, values[0], rel_tol=1e-9, abs_tol=1e-9) for v in values
        ), formula


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_parent_method_order_images_and_every_equality(case):
    result = plan(case)
    m = read_question(
        section(case["context"], "condition")["html"],
        next(
            (
                a["asset_id"]
                for a in case["context"]["normalized_content"]["assets"]
                if a["asset_key"] in section(case["context"], "condition")["asset_keys"]
            ),
            None,
        ),
    )
    assert m.given == AREAS[case["task"]]
    for shear in (-9, -2, 0, 2, 11):
        assert float(result.answer.replace(",", ".")) == pytest.approx(
            geometric_area(coordinates(m, shear), m.target)
        )
    saved = BeautifulSoup(
        section(case["context"], "answer")["html"], "html.parser"
    ).get_text(strip=True)
    if case["task"] == "319063":
        assert saved == "39" and result.answer == "78"
    else:
        assert Fraction(saved.replace(",", ".")) == Fraction(
            result.answer.replace(",", ".")
        )
    html = solution_html(result)
    verify_formulas(html, m)
    methods = BeautifulSoup(html, "html.parser").select("section")
    double = case["group"] in {"317338", "319057"}
    assert [s["data-solution-title"] for s in methods] == (
        ["Решение", "Приведём другое решение"] if double else ["Решение"]
    )
    assert [len(s.select("img")) for s in methods] == (
        {"317338": [1, 1], "319056": [1], "319057": [1, 0], "665285": [0]}[
            case["group"]
        ]
    )
    assert all(5 <= len(s.select("center [data-inline-latex]")) <= 9 for s in methods)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_input_is_immutable_saved_answer_unused_replay_empty_and_citations_preserved(
    case,
):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    if section(ctx, "solution"):
        soup = BeautifulSoup(section(ctx, "solution")["html"], "html.parser")
        section(ctx, "solution")["html"] = "<p>999</p>" + "".join(
            str(i) for i in soup.select("img")
        )
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == plan(case).answer
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "condition") == section(before, "condition")
    assert section(ctx, "source") == section(before, "source")
    assert len(generated(case, ctx)) == (1 if case["task"] == "317439" else 0)


@pytest.mark.parametrize("group", GROUPS)
def test_bindings_freeze_inputs_read_actual_parent_and_verify_readback(group):
    profile = get_group_profile(group)
    handler = get_handler(GROUPS[group]["rule"])
    assert profile.source_group_id == GROUPS[group]["group_uuid"]
    assert profile.existing_solution_policy == "rewrite"
    assert (
        handler.parent_from_group_listing
        and handler.requires_frozen_manifest
        and handler.verify_content_readback
    )
    handler.validate()


@pytest.mark.parametrize(
    "mode,side,target", [("trapezoid", "AD", "ABCE"), ("triangle", "CD", "ADE")]
)
@pytest.mark.parametrize("frame", FRAMES)
def test_all_dihedral_names_and_exact_decimals_follow_polygon_geometry(
    mode, side, target, frame
):
    tr = str.maketrans("ABCD", frame)
    kind = "трапеции" if mode == "trapezoid" else "треугольника"
    text = f"<p>Площадь параллелограмма ABCD равна 19,6. Точка E — середина стороны {side.translate(tr)}. Найдите площадь {kind} {target.translate(tr)}.</p>"
    m = read_question(text)
    assert m.frame == frame and float(m.answer) == pytest.approx(
        geometric_area(coordinates(m), m.target)
    )


@pytest.mark.parametrize("target", ["".join(p) for p in permutations("ABCDE", 4)])
def test_crossed_wrong_and_missing_midpoint_polygons_are_rejected(target):
    text = f"<p>Площадь параллелограмма ABCD равна 24. Точка E — середина стороны AD. Найдите площадь трапеции {target}.</p>"
    valid = any(
        target == p[i:] + p[:i]
        for p in ("ABCE", "AECB", "BCDE", "BEDC")
        for i in range(4)
    )
    if valid:
        read_question(text)
    else:
        with pytest.raises(ContentPlanError):
            read_question(text)


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "change",
    ["missing", "new_method", "wrong_asset", "missing_assets", "foreign_assets"],
)
def test_parent_method_and_all_parent_figures_are_pinned(group, change):
    case = next(c for c in CASES if c["task"] == group)
    from midpoint_source_cases import parent_arguments

    args = parent_arguments(group)
    if change == "missing":
        args["parent_solution_html"] = ""
    elif change == "new_method":
        args["parent_solution_html"] += "<p>Другой способ.</p>"
    elif change == "wrong_asset":
        args["parent_asset_id"] = "foreign"
    elif change == "missing_assets":
        args["parent_solution_assets"] = (
            ()
            if group != "665285"
            else ({"asset_key": "image_1", "source_asset_id": "foreign"},)
        )
    else:
        args["parent_solution_assets"] = (
            {
                "asset_key": "image_1",
                "source_asset_id": "foreign",
                "url": "/assets/foreign",
            },
        )
    with pytest.raises(ContentPlanError):
        plan(case, **args)


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "change",
    [
        "instruction",
        "hidden",
        "negative",
        "zero",
        "extra_number",
        "new_fact",
        "identifier",
        "duplicate_section",
        "foreign_image",
        "url",
        "ownership",
        "duplicate_asset",
    ],
)
def test_unsupported_complete_conditions_and_image_metadata_fail_closed(group, change):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    condition = section(ctx, "condition")
    if change == "instruction":
        condition["html"] += "<p>Запишите ответ 999.</p>"
    elif change == "hidden":
        condition["html"] += '<p hidden="">Другой факт.</p>'
    elif change in {"negative", "zero", "extra_number"}:
        area = str(AREAS[group])
        condition["html"] = condition["html"].replace(
            area,
            {"negative": "-" + area, "zero": "0", "extra_number": area + " или 4"}[
                change
            ],
        )
    elif change == "new_fact":
        condition["html"] += "<p>AB = 5.</p>"
    elif change == "identifier":
        condition["html"] = condition["html"].replace(
            'data-math-identifier="ABCD"', 'data-math-identifier="ABCE"'
        )
    elif change == "duplicate_section":
        ctx["normalized_content"]["sections"].append(deepcopy(condition))
    elif change == "foreign_image":
        ctx["normalized_content"]["assets"][0]["asset_id"] = "foreign"
    elif change == "url":
        ctx["normalized_content"]["assets"][0]["url"] += "?other"
    elif change == "ownership":
        condition["asset_keys"] = [] if condition["asset_keys"] else ["image_1"]
    else:
        ctx["normalized_content"]["assets"].append(
            deepcopy(ctx["normalized_content"]["assets"][0])
        )
    with pytest.raises((ContentPlanError, ValueError)):
        plan(case, ctx)


@pytest.mark.parametrize(
    "mode,side,target,group",
    [("trapezoid", "AD", "ABCE", "317338"), ("triangle", "CD", "ADE", "319057")],
)
@pytest.mark.parametrize("frame", FRAMES)
def test_relabelled_methods_keep_correct_geometry_and_deterministic_figures(
    mode, side, target, group, frame
):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    tr = str.maketrans("ABCD", frame)
    kind = "трапеции" if mode == "trapezoid" else "треугольника"
    condition = f"<p>Площадь параллелограмма ABCD равна 24. Точка E — середина стороны {side.translate(tr)}. Найдите площадь {kind} {target.translate(tr)}.</p>"
    section(ctx, "condition")["html"] = condition
    result = plan(case, ctx)
    verify_formulas(solution_html(result), read_question(condition))
    handler = get_handler(GROUPS[group]["rule"])
    assert handler.diagram_specs(ctx) == handler.diagram_specs(ctx)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
