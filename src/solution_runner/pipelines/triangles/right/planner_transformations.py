"""Build normalized right-triangle content transformations."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)

from .planner_notation import (
    _canonical_trig_latex,
    _decimal_reduction_latex,
    _number_latex,
    _positive_root_number_latex,
)


def _asset_transformation(parent_asset_id: str) -> dict[str, Any]:
    """Attach the parent condition image at the canonical first position."""

    return {
        "transformation_target_id": "asset:image_1",
        "operation": "add",
        "value": {
            "parent_target_id": "section:condition:1",
            "position": 0,
            "asset_key": "image_1",
            "asset_id": parent_asset_id,
            "url": f"/assets/{parent_asset_id}",
            "kind": "ordinary_image",
            "alt": "",
        },
    }


def _solution_transformation(
    trig_name: str,
    trig_latex: str,
    trig_squared: Fraction,
    cosine_latex: str,
    known: str,
    requested: str,
    answer: str,
    hypotenuse_latex: str | None,
) -> dict[str, Any]:
    """Build the compact prototype-shaped solution for the selected side rule."""

    answer_latex = answer.replace(",", "{,}")
    canonical_trig = _canonical_trig_latex(trig_latex)
    lead_rows: list[str] = []
    decimal_row = _decimal_reduction_latex(trig_name, trig_latex)
    if decimal_row is not None:
        lead_rows.append(decimal_row)
    if trig_name == "sin":
        intro = '<p>Найдём косинус угла <var data-math-identifier="A">A</var>:</p>'
        lead_rows.append(
            rf"\cos A=\sqrt{{1-\sin^2 A}}="
            rf"\sqrt{{1-\left({canonical_trig}\right)^2}}={cosine_latex}"
        )
    else:
        intro = (
            "<p>Запишем значение косинуса в виде обыкновенной дроби:</p>"
            if decimal_row is not None
            else "<p>По условию задан косинус угла "
            '<var data-math-identifier="A">A</var>:</p>'
        )
        if decimal_row is None:
            lead_rows.append(rf"\cos A={canonical_trig}")
    if requested == "AB":
        result_formula = (
            rf"AB=\frac{{AC}}{{\cos A}}="
            rf"\frac{{{known}}}{{{cosine_latex}}}={answer_latex}"
        )
    elif requested == "AC":
        result_formula = rf"AC=AB\cdot\cos A={known}\cdot {cosine_latex}={answer_latex}"
    else:
        if hypotenuse_latex is None:
            raise RightTrianglePlanError("AC-to-BC rule requires an exact hypotenuse")
        cosine_formula = (
            rf"\cos A=\sqrt{{1-\sin^{{2}} A}}="
            rf"\sqrt{{1-({canonical_trig})^{{2}}}}={cosine_latex}"
        )
        hypotenuse_formula = (
            rf"AB=\frac{{AC}}{{\cos A}}="
            rf"\frac{{{known}}}{{{cosine_latex}}}={hypotenuse_latex}"
        )
        result_formula = (
            rf"BC=\sqrt{{AB^{{2}}-AC^{{2}}}}="
            rf"\sqrt{{({hypotenuse_latex})^{{2}}-{known}^{{2}}}}="
            rf"{answer_latex}"
        )
        html = (
            '<section data-content-kind="solution" '
            'data-solution-title="Альтернативное решение.">'
            "<p><b>Альтернативное решение.</b></p>"
            "<p>Най\u00adдем ко\u00adси\u00adнус угла <i>А</i>:</p>"
            '<center><p> <span data-inline-latex="'
            + cosine_formula
            + '"></span> . </p></center>'
            "<p>Най\u00adдем длину ги\u00adпо\u00adте\u00adну\u00adзы "
            '<var data-math-identifier="AB">AB</var>:</p>'
            '<center><p> <span data-inline-latex="'
            + hypotenuse_formula
            + '"></span> . </p></center>'
            "<p>По те\u00adо\u00adре\u00adме Пи\u00adфа\u00adго\u00adра най\u00adдем длину ка\u00adте\u00adта "
            '<var data-math-identifier="BC">BC</var>:</p>'
            '<center><p> <span data-inline-latex="'
            + result_formula
            + '"></span>. </p></center></section>'
        )
        return {
            "transformation_target_id": "section:solution",
            "operation": "add",
            "value": {"title": "Решение", "html": html, "asset_keys": []},
        }
    html = (
        '<section data-content-kind="solution" data-solution-title="Решение">'
        + intro
        + "".join(
            '<center><p><span data-inline-latex="' + row + '"></span>.</p></center>'
            for row in lead_rows
        )
        + "<p>Следовательно,</p>"
        + '<center><p><span data-inline-latex="'
        + result_formula
        + '"></span>.</p></center>'
        + "</section>"
    )
    return {
        "transformation_target_id": "section:solution",
        "operation": "add",
        "value": {"title": "Решение", "html": html, "asset_keys": []},
    }


def _tangent_solution_transformation(
    trig_latex: str,
    known: str,
    known_squared: Fraction,
    bc_latex: str,
    bc_squared: Fraction,
    hypotenuse_squared: Fraction,
    answer: str,
) -> dict[str, Any]:
    """Copy the approved tangent-definition and Pythagoras solution HTML."""

    answer_latex = answer.replace(",", "{,}")
    hypotenuse_latex = _positive_root_number_latex(hypotenuse_squared)
    exact_answer = (
        hypotenuse_latex
        if hypotenuse_latex == answer_latex
        else hypotenuse_latex + "=" + answer_latex
    )
    definition_formula = r"\tg A=\frac{BC}{AC}"
    bc_formula = rf"BC=AC\cdot\tg A={known}\cdot {trig_latex}={bc_latex}"
    ab_formula = (
        rf"AB=\sqrt{{AC^{{2}}+BC^{{2}}}}="
        rf"\sqrt{{{_number_latex(known_squared)}+{_number_latex(bc_squared)}}}="
        rf"\sqrt{{{_number_latex(hypotenuse_squared)}}}={exact_answer}"
    )
    html = (
        '<section data-content-kind="solution" '
        'data-content-rule="right-triangle-tangent-hypotenuse" '
        'data-solution-title="Приведем другое решение:">'
        '<center><p><span data-inline-latex="'
        + definition_formula
        + '"></span>.</p></center>'
        '<p>Най\u00adдем <var data-math-identifier="BC">BC</var>:</p>'
        '<center><p><span data-inline-latex="' + bc_formula + '"></span>.</p></center>'
        "<p>По те\u00adо\u00adре\u00adме Пи\u00adфа\u00adго\u00adра най\u00adдем "
        '<var data-math-identifier="AB">AB</var>:</p>'
        '<center><p><span data-inline-latex="'
        + ab_formula
        + '"></span>.</p></center></section>'
    )
    return {
        "transformation_target_id": "section:solution",
        "operation": "add",
        "value": {"title": "Решение", "html": html, "asset_keys": []},
    }


def _tangent_bc_solution_transformation(
    trig_latex: str,
    known: str,
    bc_latex: str,
    answer: str,
    *,
    operation: str = "add",
) -> dict[str, Any]:
    """Build the 27243 parent calculation as one equivalence chain."""

    answer_latex = answer.replace(",", "{,}")
    exact_answer = (
        bc_latex if bc_latex == answer_latex else bc_latex + "=" + answer_latex
    )
    html = (
        '<section data-content-kind="solution" '
        'data-content-rule="right-triangle-tangent-opposite-cathetus" '
        'data-solution-title="Решение">'
        "<p>По опре\u00adде\u00adле\u00adнию тан\u00adген\u00adса:</p>"
        '<center><p><span data-inline-latex="'
        + rf"\tg A=\frac{{BC}}{{AC}}\iff BC=AC\tg A={known}\cdot {trig_latex}={exact_answer}"
        + '"></span>.</p></center></section>'
    )
    return {
        "transformation_target_id": "section:solution",
        "operation": operation,
        "value": {"title": "Решение", "html": html, "asset_keys": []},
    }


def _answer_transformation(answer: str) -> dict[str, Any]:
    """Build the canonical answer-section rewrite for one verified value."""

    return {
        "transformation_target_id": "section:answer:1",
        "operation": "rewrite",
        "value": {
            "title": "Ответ",
            "html": f'<p><span data-effect="spaced">{answer}</span></p>',
            "asset_keys": [],
        },
    }


def _elementary_solution_transformation(
    content_rule_key: str,
    intro: str,
    rows: list[str],
    *,
    operation: str = "add",
) -> dict[str, Any]:
    """Wrap one elementary right-triangle derivation without formula punctuation."""

    rendered_rows = []
    for index, row in enumerate(rows):
        rendered_rows.append(
            '<center><p><span data-inline-latex="' + row + '"></span></p></center>'
        )
        if content_rule_key == "right-triangle-median-angle" and index == 0:
            rendered_rows.append(
                '<p>Значит, <span data-inline-latex="\\triangle ACD"></span> '
                "равнобедренный, поэтому его углы при основании равны:</p>"
            )
    html = (
        '<section data-content-kind="solution" data-content-rule="'
        + content_rule_key
        + '" data-solution-title="Решение">'
        + intro
        + "".join(rendered_rows)
        + "</section>"
    )
    return {
        "transformation_target_id": "section:solution",
        "operation": operation,
        "value": {"title": "Решение", "html": html, "asset_keys": []},
    }
