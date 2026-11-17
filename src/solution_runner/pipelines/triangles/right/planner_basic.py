"""Build right-triangle repairs from the parent solution or exact trig values."""

from __future__ import annotations

import math
import re
from fractions import Fraction
from html import unescape
from typing import Any

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)

from .planner_common import RepairPlan, _parent_triangle_plan, _section
from .planner_conditions import _plain_html
from .planner_notation import (
    _answer_text,
    _numeric_latex,
    _numeric_square_latex,
    _positive_root_latex,
    _positive_root_number_latex,
    _trig_square,
)
from .planner_transformations import (
    _answer_transformation,
    _asset_transformation,
    _solution_transformation,
    _tangent_bc_solution_transformation,
    _tangent_solution_transformation,
)
from .planner_universal_parse import _latex_values


def _is_pipeline_verbose_solution(value: str) -> bool:
    """Recognize only the mechanical multi-row solution emitted by this runner."""

    if 'data-content-kind="solution"' not in value:
        return False
    formulas = re.findall(r'data-inline-latex="([^"]+)"', unescape(value))
    if r"\cos^2 A=1-\sin^2 A" in formulas:
        return True
    return (
        len(formulas) >= 4
        and r"\cos A=\frac{AC}{AB}" in formulas
        and any(
            formula in {r"AB=\frac{AC}{\cos A}", r"AC=AB\cdot\cos A"}
            for formula in formulas
        )
    )


def _is_pipeline_unsimplified_root_solution(value: str) -> bool:
    """Recognize the runner's former sqrt(n*d)/d rationalization shape."""

    if 'data-content-kind="solution"' not in value:
        return False
    for radicand, denominator in re.findall(
        r"\\frac\{\\sqrt\{(\d+)\}\}\{(\d+)\}",
        unescape(value),
    ):
        parsed_radicand = int(radicand)
        parsed_denominator = int(denominator)
        root = math.isqrt(parsed_denominator)
        if (
            root * root == parsed_denominator
            and parsed_radicand % parsed_denominator == 0
        ):
            return True
    return False


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_asset_id: str,
    parent_solution_html: str | None = None,
    required_trig_name: str | None = None,
    required_requested: str | None = None,
) -> RepairPlan:
    """Return minimal image, solution, and answer transformations for one task."""

    if parent_solution_html is not None:
        return _parent_triangle_plan(
            context,
            parent_asset_id,
            parent_solution_html,
            required_trig_name=required_trig_name,
            required_requested=required_requested,
        )
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    trig_name, trig_latex, _known_side, known, requested = _latex_values(
        str(condition.get("html") or "")
    )
    if required_trig_name is not None and trig_name != required_trig_name:
        raise RightTrianglePlanError(f"condition must use {required_trig_name} A")
    if required_requested is not None and requested != required_requested:
        raise RightTrianglePlanError(f"condition must request {required_requested}")
    if (_known_side, requested) not in {
        ("AC", "AB"),
        ("AB", "AC"),
        ("AC", "BC"),
    }:
        raise RightTrianglePlanError("condition is outside the supported side rules")
    if requested == "BC" and trig_name != "sin":
        raise RightTrianglePlanError("AC-to-BC rule requires sin A")
    trig_squared = _trig_square(trig_latex)
    if trig_name == "tg" and trig_squared <= 0:
        raise RightTrianglePlanError("tg A must be positive")
    if trig_name != "tg" and not 0 < trig_squared < 1:
        raise RightTrianglePlanError("sin A or cos A must be between zero and one")
    known_value = _numeric_latex(known)
    known_squared = _numeric_square_latex(known)
    cosine_latex = ""
    hypotenuse_latex = None
    bc_squared = Fraction(0)
    hypotenuse_squared = Fraction(0)
    bc_latex = ""
    if trig_name == "tg":
        bc_squared = known_squared * trig_squared
        hypotenuse_squared = known_squared + bc_squared
        bc_latex = _positive_root_number_latex(bc_squared)
        answer_value = math.sqrt(float(hypotenuse_squared))
    else:
        cosine_squared = 1 - trig_squared if trig_name == "sin" else trig_squared
        cosine_latex = _positive_root_latex(cosine_squared)
        cosine = math.sqrt(float(cosine_squared))
    if trig_name != "tg" and requested == "AB":
        answer_value = known_value / cosine
    elif trig_name != "tg" and requested == "AC":
        answer_value = known_value * cosine
    elif trig_name != "tg":
        hypotenuse_squared = known_squared / cosine_squared
        hypotenuse_latex = _positive_root_latex(hypotenuse_squared)
        answer_value = math.sqrt(float(hypotenuse_squared - known_squared))
    answer = _answer_text(answer_value)
    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if (
        not isinstance(current_asset, dict)
        or current_asset.get("asset_id") != parent_asset_id
    ):
        transformations.append(_asset_transformation(parent_asset_id))
    solution = _section(content, "solution")
    solution_html = str(solution.get("html") or "") if solution is not None else ""
    if (
        solution is None
        or not _plain_html(solution_html)
        or _is_pipeline_verbose_solution(solution_html)
        or _is_pipeline_unsimplified_root_solution(solution_html)
        or (requested == "BC" and "<img" in solution_html)
        or (
            trig_name == "tg"
            and 'data-content-rule="right-triangle-tangent-hypotenuse"'
            not in solution_html
        )
    ):
        if trig_name == "tg":
            transformations.append(
                _tangent_solution_transformation(
                    trig_latex,
                    known,
                    known_squared,
                    bc_latex,
                    bc_squared,
                    hypotenuse_squared,
                    answer,
                )
            )
        else:
            transformations.append(
                _solution_transformation(
                    trig_name,
                    trig_latex,
                    trig_squared,
                    cosine_latex,
                    known,
                    requested,
                    answer,
                    hypotenuse_latex,
                )
            )
    if (
        answer_section is None
        or _plain_html(str(answer_section.get("html") or "")) != answer
    ):
        transformations.append(_answer_transformation(answer))
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_tangent_bc_repair_plan(
    context: dict[str, Any],
    *,
    parent_asset_id: str,
    parent_solution_html: str | None = None,
) -> RepairPlan:
    """Return strict AC-and-tangent repairs for tasks requesting BC."""

    if parent_solution_html is not None:
        return _parent_triangle_plan(
            context,
            parent_asset_id,
            parent_solution_html,
            required_trig_name="tg",
            required_requested="BC",
        )
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    trig_name, trig_latex, known_side, known, requested = _latex_values(
        str(condition.get("html") or "")
    )
    if trig_name != "tg":
        raise RightTrianglePlanError("condition must use tg A")
    if requested != "BC":
        raise RightTrianglePlanError("condition must request BC")
    if known_side != "AC":
        raise RightTrianglePlanError("condition must give AC")
    tangent_squared = _trig_square(trig_latex)
    if tangent_squared <= 0:
        raise RightTrianglePlanError("tg A must be positive")
    known_squared = _numeric_square_latex(known)
    bc_squared = known_squared * tangent_squared
    bc_latex = _positive_root_number_latex(bc_squared)
    answer = _answer_text(math.sqrt(float(bc_squared)))
    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if (
        not isinstance(current_asset, dict)
        or current_asset.get("asset_id") != parent_asset_id
    ):
        transformations.append(_asset_transformation(parent_asset_id))
    solution = _section(content, "solution")
    solution_html = str(solution.get("html") or "") if solution is not None else ""
    desired_solution = _tangent_bc_solution_transformation(
        trig_latex,
        known,
        bc_latex,
        answer,
    )
    if solution is None or not _plain_html(solution_html):
        transformations.append(desired_solution)
    elif (
        'data-content-rule="right-triangle-tangent-opposite-cathetus"' in solution_html
        and solution_html != desired_solution["value"]["html"]
    ):
        transformations.append(
            _tangent_bc_solution_transformation(
                trig_latex,
                known,
                bc_latex,
                answer,
                operation="rewrite",
            )
        )
    if (
        answer_section is None
        or _plain_html(str(answer_section.get("html") or "")) != answer
    ):
        transformations.append(_answer_transformation(answer))
    return RepairPlan(answer=answer, transformations=tuple(transformations))
