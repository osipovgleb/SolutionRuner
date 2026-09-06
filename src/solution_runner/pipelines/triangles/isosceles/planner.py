"""Parse isosceles-triangle conditions and build minimal content repairs."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape, unescape
import math
import re
from typing import Any

import sympy as sp
from bs4 import BeautifulSoup, Tag


class IsoscelesTrianglePlanError(ValueError):
    """Report an unsupported or inconsistent isosceles-triangle task."""


@dataclass(frozen=True)
class RepairPlan:
    """Carry one exact answer and the transformations needed to reach it."""

    answer: str
    transformations: tuple[dict[str, Any], ...]


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Return one unique normalized section by canonical key."""

    matches = [
        item
        for item in content.get("sections", [])
        if isinstance(item, dict) and item.get("key") == key
    ]
    if len(matches) > 1:
        raise IsoscelesTrianglePlanError(f"multiple {key} sections are present")
    return matches[0] if matches else None


def _plain_html(value: str) -> str:
    """Return visible normalized text for emptiness and answer checks."""

    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _formula_text(value: str) -> str:
    """Restore inline LaTeX attributes into their visible source positions."""

    value = value.replace("\u00ad", "")
    restored = re.sub(
        r'<[^>]*\bdata-inline-latex=["\']([^"\']*)["\'][^>]*>.*?</[^>]+>',
        lambda match: " " + unescape(match.group(1)) + " ",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", restored))).strip()


def _split_braced(value: str, start: int) -> tuple[str, int]:
    """Return one balanced braced token and the first following position."""

    if start >= len(value) or value[start] != "{":
        raise IsoscelesTrianglePlanError("unsupported exact value")
    depth = 0
    for index in range(start, len(value)):
        if value[index] == "{":
            depth += 1
        elif value[index] == "}":
            depth -= 1
            if depth == 0:
                return value[start + 1 : index], index + 1
    raise IsoscelesTrianglePlanError("unbalanced exact value")


def _parse_positive_value(value: str) -> sp.Expr:
    """Parse a positive rational or one quadratic-radical LaTeX value."""

    compact = (
        value.replace(r"\left", "")
        .replace(r"\right", "")
        .replace(" ", "")
        .replace("{,}", ".")
        .replace(",", ".")
    )
    if compact.startswith(r"\frac"):
        numerator, next_index = _split_braced(compact, len(r"\frac"))
        denominator, final_index = _split_braced(compact, next_index)
        if final_index != len(compact):
            raise IsoscelesTrianglePlanError(f"unsupported exact value: {value}")
        parsed = _parse_positive_value(numerator) / _parse_positive_value(denominator)
    else:
        radical = re.fullmatch(r"(\d+(?:\.\d+)?)?\\sqrt\{(\d+)\}", compact)
        if radical is not None:
            parsed = sp.Rational(radical.group(1) or "1") * sp.sqrt(
                int(radical.group(2))
            )
        elif re.fullmatch(r"\d+(?:\.\d+)?", compact):
            parsed = sp.Rational(compact)
        else:
            raise IsoscelesTrianglePlanError(f"unsupported exact value: {value}")
    parsed = sp.simplify(parsed)
    if parsed.is_real is not True or parsed.is_positive is not True:
        raise IsoscelesTrianglePlanError("condition values must be positive")
    return parsed


def _latex_number(value: sp.Expr) -> str:
    """Render one exact positive expression in compact LaTeX form."""

    return sp.latex(sp.simplify(value)).replace(r" \sqrt", r"\sqrt")


def _answer_text(value: sp.Expr) -> str:
    """Render one finite result with the source's decimal-comma convention."""

    numeric = float(sp.N(value, 15))
    if not math.isfinite(numeric):
        raise IsoscelesTrianglePlanError("computed answer is not finite")
    rounded = round(numeric, 10)
    if math.isclose(rounded, round(rounded), abs_tol=1e-9):
        return str(round(rounded))
    return f"{rounded:.10f}".rstrip("0").rstrip(".").replace(".", ",")


def _target(section: dict[str, Any] | None, key: str) -> str:
    """Return the exact current section target or its canonical add target."""

    if section is not None:
        exact = str(section.get("transformation_target_id") or "")
        if exact:
            return exact
        section_id = str(section.get("section_id") or "")
        if section_id:
            return f"section:{section_id}"
    return f"section:{key}"


def _section_transformation(
    section: dict[str, Any] | None,
    key: str,
    title: str,
    html: str,
    *,
    asset_keys: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Build one exact add or rewrite operation for a normalized section."""

    return {
        "transformation_target_id": _target(section, key),
        "operation": "rewrite" if section is not None else "add",
        "value": {"title": title, "html": html, "asset_keys": list(asset_keys)},
    }


def _asset_transformation(parent_condition_asset_id: str) -> dict[str, Any]:
    """Attach the parent condition image at the canonical first position."""

    return {
        "transformation_target_id": "asset:image_1",
        "operation": "add",
        "value": {
            "parent_target_id": "section:condition:1",
            "position": 0,
            "asset_key": "image_1",
            "asset_id": parent_condition_asset_id,
            "url": f"/assets/{parent_condition_asset_id}",
            "kind": "ordinary_image",
            "alt": "",
            "html": (
                f'<center><img alt="" data-asset-id="{parent_condition_asset_id}" '
                f'data-asset-key="image_1" src="/assets/{parent_condition_asset_id}"/></center>'
            ),
        },
    }


def _without_asset_markup(section: dict[str, Any], asset_key: str) -> tuple[str, tuple[str, ...]]:
    """Remove one misplaced image while preserving all substantive section content."""

    soup = BeautifulSoup(str(section.get("html") or ""), "html.parser")
    for image in list(soup.find_all("img", attrs={"data-asset-key": asset_key})):
        wrapper = image.parent
        image.decompose()
        if (
            isinstance(wrapper, Tag)
            and wrapper.name in {"p", "center", "figure"}
            and not wrapper.get_text(strip=True)
            and wrapper.find(("img", "audio", "video")) is None
        ):
            wrapper.decompose()
    keys = tuple(
        str(value)
        for value in section.get("asset_keys", [])
        if str(value) and str(value) != asset_key
    )
    return str(soup), keys


def _solution_asset_transformation(
    asset: dict[str, str],
    *,
    expected_asset_key: str,
) -> dict[str, Any]:
    """Attach one parent-owned solution image to the canonical solution section."""

    asset_key = str(asset.get("asset_key") or "")
    asset_id = str(asset.get("source_asset_id") or "")
    url = str(asset.get("url") or f"/assets/{asset_id}")
    alt = str(asset.get("alt") or "")
    if asset_key != expected_asset_key or not asset_id:
        raise IsoscelesTrianglePlanError(
            f"parent must provide exactly solution asset {expected_asset_key}"
        )
    html = (
        f'<center><img alt="{escape(alt, quote=True)}" '
        f'data-asset-id="{escape(asset_id, quote=True)}" '
        f'data-asset-key="{escape(asset_key, quote=True)}" '
        f'src="{escape(url, quote=True)}"/></center>'
    )
    return {
        "transformation_target_id": f"asset:{asset_key}",
        "operation": "add",
        "value": {
            "parent_target_id": "section:solution",
            "position": 0,
            "asset_key": asset_key,
            "asset_id": asset_id,
            "url": url,
            "kind": "ordinary_image",
            "alt": alt,
            "html": html,
        },
    }


def _condition_asset_transformation(
    asset: dict[str, str],
    *,
    expected_asset_key: str,
) -> dict[str, Any]:
    """Move one parent-owned diagram to the centered condition position."""

    asset_key = str(asset.get("asset_key") or "")
    asset_id = str(asset.get("source_asset_id") or "")
    url = str(asset.get("url") or f"/assets/{asset_id}")
    alt = str(asset.get("alt") or "")
    if asset_key != expected_asset_key or not asset_id:
        raise IsoscelesTrianglePlanError(
            f"parent must provide exactly condition asset {expected_asset_key}"
        )
    html = (
        f'<center><img alt="{escape(alt, quote=True)}" '
        f'data-asset-id="{escape(asset_id, quote=True)}" '
        f'data-asset-key="{escape(asset_key, quote=True)}" '
        f'src="{escape(url, quote=True)}"/></center>'
    )
    return {
        "transformation_target_id": f"asset:{asset_key}",
        "operation": "add",
        "value": {
            "parent_target_id": "section:condition:1",
            "position": 0,
            "asset_key": asset_key,
            "asset_id": asset_id,
            "url": url,
            "kind": "ordinary_image",
            "alt": alt,
            "html": html,
        },
    }


def _condition_image_repairs(
    content: dict[str, Any],
    parent_solution_assets: tuple[dict[str, str], ...],
    *,
    group_key: str,
) -> tuple[dict[str, Any], ...]:
    """Place the prototype diagram in condition and remove its solution occurrence."""

    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(str(solution.get("html") or ""))
    solution_has_image = solution is not None and (
        "image_1" in tuple(str(value) for value in solution.get("asset_keys", []))
        or BeautifulSoup(str(solution.get("html") or ""), "html.parser").find(
            "img", attrs={"data-asset-key": "image_1"}
        )
        is not None
    )
    if not solution_missing and not solution_has_image:
        return ()
    image_assets = [
        item for item in parent_solution_assets if item.get("asset_key") == "image_1"
    ]
    if len(image_assets) != 1:
        raise IsoscelesTrianglePlanError(
            f"group {group_key} parent must provide primary image_1"
        )
    transformations: list[dict[str, Any]] = [
        _condition_asset_transformation(image_assets[0], expected_asset_key="image_1")
    ]
    if solution is not None and solution_has_image:
        cleaned_html, remaining_keys = _without_asset_markup(solution, "image_1")
        transformations.insert(
            0,
            _section_transformation(
                solution,
                "solution",
                str(solution.get("title") or "Решение"),
                cleaned_html,
                asset_keys=remaining_keys,
            ),
        )
    return tuple(transformations)


def _parse_base_from_sine(condition_html: str) -> tuple[sp.Expr, str, sp.Expr, str]:
    """Return equal side, base angle, sine value, and its source LaTeX."""

    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    requested = formula.split("Найд", 1)[-1] if "Найд" in formula else ""
    if not re.search(r"\bAB\b", requested) or re.search(r"\b(?:AC|BC|AH|BH|CH)\b", requested):
        raise IsoscelesTrianglePlanError("condition must request AB")
    side_match = re.search(r"(?:AC\s*=\s*BC|BC\s*=\s*AC)\s*=\s*([^,;.]+)", formula)
    sine_match = re.search(r"\\sin\s*([AB])\s*=\s*([^,;.]+)", formula)
    if side_match is None or sine_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and sin A or sin B")
    side_latex = side_match.group(1).strip()
    sine_latex = sine_match.group(2).strip()
    side = _parse_positive_value(side_latex)
    sine = _parse_positive_value(sine_latex)
    if sp.simplify(1 - sine**2).is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle sine must be less than one")
    return side, sine_match.group(1), sine, sine_latex


def _inline_formulas(value: str) -> tuple[str, ...]:
    """Return decoded inline LaTeX values in document order."""

    return tuple(
        unescape(match)
        for match in re.findall(
            r'\bdata-inline-latex=["\']([^"\']*)["\']',
            value,
            flags=re.IGNORECASE,
        )
    )


def _parse_equal_side_from_base_and_sine(
    condition_html: str,
) -> tuple[sp.Expr, sp.Expr, str]:
    """Return the known base and sine for the strict group-27285 contract."""

    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    requested = formula.split("Найд", 1)[-1] if "Найд" in formula else ""
    if not re.search(r"\bAC\b", requested) or re.search(
        r"\b(?:AB|BC|AH|BH|CH)\b", requested
    ):
        raise IsoscelesTrianglePlanError("condition must request AC")
    if re.search(r"(?:AC\s*=\s*BC|BC\s*=\s*AC)", formula) is None:
        raise IsoscelesTrianglePlanError("condition must state AC=BC")
    inline = _inline_formulas(condition_html)
    base_latex = next(
        (item.split("=", 1)[1].strip() for item in inline if item.startswith("AB=")),
        "",
    )
    if not base_latex:
        base_match = re.search(
            r"\bAB\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
            r"\d+(?:\{,\}\d+|[.,]\d+)?)",
            formula,
        )
        base_latex = base_match.group(1) if base_match is not None else ""
    sine_latex = next(
        (
            item.split("=", 1)[1].strip()
            for item in inline
            if re.match(r"\\sin\s*A\s*=", item)
        ),
        "",
    )
    if not base_latex or not sine_latex:
        raise IsoscelesTrianglePlanError("condition must give AB and sin A")
    base = _parse_positive_value(base_latex)
    sine = _parse_positive_value(sine_latex)
    if sp.simplify(1 - sine**2).is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle sine must be less than one")
    return base, sine, sine_latex


def _solution_html(
    side: sp.Expr,
    angle: str,
    sine: sp.Expr,
    sine_latex: str,
    answer: str,
) -> str:
    """Adapt the selected parent solution while preserving its proof shape."""

    cosine = sp.sqrt(sp.simplify(1 - sine**2))
    side_latex = _latex_number(side)
    cosine_latex = _latex_number(cosine)
    answer_latex = answer.replace(",", "{,}")
    formula = (
        rf"AB=2AH=2AC\cos {angle}=2AC\sqrt{{1-\sin^{{2}} {angle}}}="
        rf"2\cdot {side_latex}\sqrt{{1-({sine_latex})^{{2}}}}="
        rf"{_latex_number(2 * side)}\cdot {cosine_latex}={answer_latex}"
    )
    return (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому высота <span data-inline-latex="CH"></span> '
        'делит основание <span data-inline-latex="AB"></span> пополам. '
        'Следовательно,</p><center><p><span data-inline-latex="'
        + formula
        + '"></span>.</p></center>'
    )


def _group_27285_solution_html(
    base: sp.Expr,
    sine: sp.Expr,
    sine_latex: str,
    answer: str,
) -> str:
    """Adapt the inverse parent proof for the exact group-27285 contract."""

    formula = (
        r"AC=\frac{AH}{\cos A}=\frac{AB}{2\cos A}="
        r"\frac{AB}{2\sqrt{1-\sin^{2} A}}="
        rf"\frac{{{_latex_number(base)}}}{{2\sqrt{{1-({sine_latex})^{{2}}}}}}="
        + answer.replace(",", "{,}")
    )
    return (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому высота <span data-inline-latex="CH"></span> '
        'делит основание <span data-inline-latex="AB"></span> пополам. '
        'Тогда</p><center><p><span data-inline-latex="'
        + formula
        + '"></span>.</p></center>'
    )


def _request_text(condition_html: str) -> str:
    """Return the normalized tail beginning at the source's request verb."""

    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    return formula.split("Найд", 1)[-1] if "Найд" in formula else ""


def _inline_assignment(condition_html: str, pattern: str) -> str:
    """Return the right-hand side of one uniquely matched inline assignment."""

    matches = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(pattern, item)
    ]
    if len(matches) != 1:
        raise IsoscelesTrianglePlanError("condition assignment is missing or ambiguous")
    return matches[0]


def _build_missing_solution_plan(
    content: dict[str, Any],
    *,
    answer: str,
    solution_html: str,
    parent_condition_asset_id: str,
    ensure_condition_asset: bool = False,
    refresh_solution: bool = False,
) -> RepairPlan:
    """Build shared minimal writes after one group-specific proof is solved."""

    transformations: list[dict[str, Any]] = []
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(str(solution.get("html") or ""))
    solution_needs_write = solution_missing or (
        refresh_solution
        and solution is not None
        and str(solution.get("html") or "") != solution_html
    )
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    solution_has_image = solution is not None and (
        "image_1" in tuple(str(value) for value in solution.get("asset_keys", []))
        or BeautifulSoup(str(solution.get("html") or ""), "html.parser").find(
            "img", attrs={"data-asset-key": "image_1"}
        )
        is not None
    )
    condition_keys = tuple(str(value) for value in condition.get("asset_keys", []))
    condition_has_image = (
        "image_1" in condition_keys
        and bool(
            BeautifulSoup(str(condition.get("html") or ""), "html.parser").find(
                "img", attrs={"data-asset-key": "image_1"}
            )
        )
    )
    condition_asset_repair = (ensure_condition_asset or solution_missing or solution_has_image) and (
        not condition_has_image
        or not isinstance(current_asset, dict)
        or current_asset.get("asset_id") != parent_condition_asset_id
    )
    if solution is not None and solution_has_image and not solution_needs_write:
        cleaned_html, remaining_keys = _without_asset_markup(solution, "image_1")
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                str(solution.get("title") or "Решение"),
                cleaned_html,
                asset_keys=remaining_keys,
            )
        )
    if condition_asset_repair:
        transformations.append(_asset_transformation(parent_condition_asset_id))
    if solution_needs_write:
        transformations.append(
            _section_transformation(solution, "solution", "Решение", solution_html)
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def _normalized_content(context: dict[str, Any]) -> dict[str, Any]:
    """Return one validated schema-v3 normalized content object."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise IsoscelesTrianglePlanError("schema-v3 Normalized content is required")
    return content


def _answer_matches(section: dict[str, Any] | None, expected: str) -> bool:
    """Return whether the current answer is numerically equal to expected."""

    if section is None:
        return False
    current = _plain_html(str(section.get("html") or "")).replace(" ", "")
    try:
        return sp.Rational(current.replace(",", ".")) == sp.Rational(
            expected.replace(",", ".")
        )
    except (TypeError, ValueError):
        return False


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build the minimal group-27284 repair and preserve existing solutions."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise IsoscelesTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    side, angle, sine, sine_latex = _parse_base_from_sine(
        str(condition.get("html") or "")
    )
    answer = _answer_text(2 * side * sp.sqrt(sp.simplify(1 - sine**2)))
    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if not isinstance(current_asset, dict) or current_asset.get("asset_id") != parent_condition_asset_id:
        transformations.append(_asset_transformation(parent_condition_asset_id))
    solution = _section(content, "solution")
    if solution is None or not _plain_html(str(solution.get("html") or "")):
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                _solution_html(side, angle, sine, sine_latex, answer),
            )
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_group_27285_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the AB-and-sine to equal-side repair used by group 27285."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise IsoscelesTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    base, sine, sine_latex = _parse_equal_side_from_base_and_sine(
        str(condition.get("html") or "")
    )
    answer = _answer_text(base / (2 * sp.sqrt(sp.simplify(1 - sine**2))))
    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if not isinstance(current_asset, dict) or current_asset.get("asset_id") != parent_condition_asset_id:
        transformations.append(_asset_transformation(parent_condition_asset_id))
    solution = _section(content, "solution")
    if solution is None or not _plain_html(str(solution.get("html") or "")):
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                _group_27285_solution_html(base, sine, sine_latex, answer),
            )
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_group_27286_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-cosine to base repair for group 27286."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    requested = _request_text(condition_html)
    if not re.search(r"\bAB\b", requested) or re.search(
        r"\b(?:AC|BC|AH|BH|CH)\b", requested
    ):
        raise IsoscelesTrianglePlanError("condition must request AB")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    side_match = re.search(
        r"(?:AC\s*=\s*BC|BC\s*=\s*AC)\s*=\s*"
        r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC")
    cosine_latex = _inline_assignment(condition_html, r"\\cos\s*A\s*=")
    side = _parse_positive_value(side_match.group(1))
    cosine = _parse_positive_value(cosine_latex)
    if cosine >= 1:
        raise IsoscelesTrianglePlanError("base-angle cosine must be less than one")
    answer = _answer_text(2 * side * cosine)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому высота <span data-inline-latex="CH"></span> '
        'делит основание <span data-inline-latex="AB"></span> пополам. '
        'Тогда</p><center><p><span data-inline-latex="'
        rf"AB=2AH=2AC\cos A=2\cdot {_latex_number(side)}\cdot "
        + cosine_latex
        + "="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27287_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the base-and-cosine to equal-side repair for group 27287."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    requested = _request_text(condition_html)
    if not re.search(r"\bAC\b", requested) or re.search(
        r"\b(?:AB|BC|AH|BH|CH)\b", requested
    ):
        raise IsoscelesTrianglePlanError("condition must request AC")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if re.search(r"(?:AC\s*=\s*BC|BC\s*=\s*AC)", formula) is None:
        raise IsoscelesTrianglePlanError("condition must state AC=BC")
    inline_base = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(r"AB\s*=", item)
    ]
    base_match = re.search(
        r"\bAB\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    base_latex = (
        inline_base[0]
        if len(inline_base) == 1
        else base_match.group(1) if not inline_base and base_match is not None else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give AB")
    cosine_latex = _inline_assignment(condition_html, r"\\cos\s*A\s*=")
    base = _parse_positive_value(base_latex)
    cosine = _parse_positive_value(cosine_latex)
    if cosine >= 1:
        raise IsoscelesTrianglePlanError("base-angle cosine must be less than one")
    answer = _answer_text(base / (2 * cosine))
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому высота <span data-inline-latex="CH"></span> '
        'делит основание <span data-inline-latex="AB"></span> пополам. '
        'Тогда</p><center><p><span data-inline-latex="'
        r"AC=\frac{AH}{\cos A}=\frac{AB}{2\cos A}="
        rf"\frac{{{_latex_number(base)}}}{{2\cdot {cosine_latex}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27288_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-tangent to base repair for group 27288."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    requested = _request_text(condition_html)
    if not re.search(r"\bAB\b", requested) or re.search(
        r"\b(?:AC|BC|AH|BH|CH)\b", requested
    ):
        raise IsoscelesTrianglePlanError("condition must request AB")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    side_match = re.search(
        r"(?:AC\s*=\s*BC|BC\s*=\s*AC)\s*=\s*"
        r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC")
    tangent_latex = _inline_assignment(condition_html, r"\\tg\s*A\s*=")
    side = _parse_positive_value(side_match.group(1))
    tangent = _parse_positive_value(tangent_latex)
    cosine = sp.sqrt(sp.simplify(1 / (1 + tangent**2)))
    answer = _answer_text(2 * side * cosine)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому высота <span data-inline-latex="CH"></span> '
        'делит основание <span data-inline-latex="AB"></span> пополам. '
        'Следовательно,</p><center><p><span data-inline-latex="'
        r"AB=2AH=2AC\cos A=2AC\sqrt{\frac{1}{1+\tg^{2} A}}="
        rf"2\cdot {_latex_number(side)}\cdot "
        rf"\sqrt{{\frac{{1}}{{1+({tangent_latex})^{{2}}}}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27289_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the base-and-tangent to equal-side repair for group 27289."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    requested = _request_text(condition_html)
    if not re.search(r"\bAC\b", requested) or re.search(
        r"\b(?:AB|BC|AH|BH|CH)\b", requested
    ):
        raise IsoscelesTrianglePlanError("condition must request AC")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if re.search(r"(?:AC\s*=\s*BC|BC\s*=\s*AC)", formula) is None:
        raise IsoscelesTrianglePlanError("condition must state AC=BC")
    inline_base = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(r"AB\s*=", item)
    ]
    base_match = re.search(
        r"\bAB\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+)?)",
        formula,
    )
    base_latex = (
        inline_base[0]
        if len(inline_base) == 1
        else base_match.group(1) if not inline_base and base_match is not None else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give AB")
    tangent_latex = _inline_assignment(condition_html, r"\\tg\s*A\s*=")
    base = _parse_positive_value(base_latex)
    tangent = _parse_positive_value(tangent_latex)
    cosine = sp.sqrt(sp.simplify(1 / (1 + tangent**2)))
    answer = _answer_text(base / (2 * cosine))
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(str(solution.get("html") or ""))
    transformations: list[dict[str, Any]] = []
    if solution_missing:
        if len(parent_solution_assets) != 1:
            raise IsoscelesTrianglePlanError(
                "group 27289 parent must provide one solution asset"
            )
        current_condition_asset = next(
            (
                item
                for item in content.get("assets", [])
                if isinstance(item, dict) and item.get("asset_key") == "image_1"
            ),
            None,
        )
        if (
            not isinstance(current_condition_asset, dict)
            or current_condition_asset.get("asset_id") != parent_condition_asset_id
        ):
            transformations.append(_asset_transformation(parent_condition_asset_id))
        solution_asset = parent_solution_assets[0]
        solution_asset_transformation = _solution_asset_transformation(
            solution_asset,
            expected_asset_key="image_2",
        )
        image_html = str(solution_asset_transformation["value"]["html"])
        solution_html = (
            image_html
            + '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            'равнобедренный, поэтому высота <span data-inline-latex="CH"></span> '
            'делит основание <span data-inline-latex="AB"></span> пополам. '
            'Тогда</p><center><p><span data-inline-latex="'
            r"AC=\frac{AH}{\cos A}=\frac{AB}{2\cos A}="
            r"\frac{AB}{2\sqrt{\frac{1}{1+\tg^{2} A}}}="
            rf"\frac{{{_latex_number(base)}}}{{2\sqrt{{\frac{{1}}{{1+({tangent_latex})^{{2}}}}}}}}="
            + answer.replace(",", "{,}")
            + '"></span>.</p></center>'
        )
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                solution_html,
                asset_keys=("image_2",),
            )
        )
        transformations.append(solution_asset_transformation)
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_group_27320_repair_plan(
    context: dict[str, Any],
    *,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the base-and-sine to opposite-side altitude repair for 27320."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    equal_match = re.search(r"\b(AB|AC|BC)\s*=\s*(AB|AC|BC)\b", formula)
    if equal_match is None or equal_match.group(1) == equal_match.group(2):
        raise IsoscelesTrianglePlanError("condition must state two equal sides")
    equal_sides = {equal_match.group(1), equal_match.group(2)}
    all_sides = {"AB", "AC", "BC"}
    base_candidates = all_sides - equal_sides
    if len(base_candidates) != 1:
        raise IsoscelesTrianglePlanError("equal sides do not determine one base")
    base_name = next(iter(base_candidates))
    inline_bases = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(rf"{base_name}\s*=", item)
    ]
    visible_base = re.search(
        rf"\b{base_name}\s*=\s*((?:\d+(?:\{{,\}}\d+|[.,]\d+)?)?"
        r"\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    base_latex = (
        inline_bases[0]
        if len(inline_bases) == 1
        else visible_base.group(1)
        if not inline_bases and visible_base is not None
        else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give exactly one base length")
    sine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\sin\s*[ABC]{3}\s*=", item)
    ]
    if len(sine_assignments) != 1:
        raise IsoscelesTrianglePlanError(
            "condition must give one sine of a named base angle"
        )
    sine_match = re.match(r"\\sin\s*([ABC]{3})\s*=\s*(.+)", sine_assignments[0])
    if sine_match is None:
        raise IsoscelesTrianglePlanError("sine assignment is malformed")
    angle_name, sine_latex = sine_match.groups()
    base_vertices = set(base_name)
    angle_vertex = angle_name[1]
    if angle_vertex not in base_vertices:
        raise IsoscelesTrianglePlanError("given angle must be a base angle")
    request = _request_text(condition_html)
    altitude_matches = re.findall(r"\b([ABC]H)\b", request)
    if altitude_matches != [f"{angle_vertex}H"]:
        raise IsoscelesTrianglePlanError(
            "condition must request the altitude from the given base-angle vertex"
        )
    base = _parse_positive_value(base_latex)
    sine = _parse_positive_value(sine_latex)
    if sine >= 1:
        raise IsoscelesTrianglePlanError("base-angle sine must be less than one")
    answer = _answer_text(base * sine)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(str(solution.get("html") or ""))
    transformations = list(
        _condition_image_repairs(content, parent_solution_assets, group_key="27320")
    )
    if solution_missing:
        other_base_vertex = next(iter(base_vertices - {angle_vertex}))
        solution_html = (
            '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            'равнобедренный, поэтому углы при его основании равны. Тогда</p>'
            '<center><p><span data-inline-latex="'
            + f"{angle_vertex}H={base_name}\\sin \\angle "
            + f"{angle_vertex}{other_base_vertex}H={base_name}\\sin \\angle {angle_name}="
            + rf"{_latex_number(base)}\cdot {sine_latex}="
            + answer.replace(",", "{,}")
            + '"></span>.</p></center>'
        )
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                solution_html,
            )
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_group_27321_repair_plan(
    context: dict[str, Any],
    *,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the base-and-sine to adjacent projection repair for 27321."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    equal_match = re.search(r"\b(AB|AC|BC)\s*=\s*(AB|AC|BC)\b", formula)
    if equal_match is None or equal_match.group(1) == equal_match.group(2):
        raise IsoscelesTrianglePlanError("condition must state two equal sides")
    base_candidates = {"AB", "AC", "BC"} - {
        equal_match.group(1),
        equal_match.group(2),
    }
    if len(base_candidates) != 1:
        raise IsoscelesTrianglePlanError("equal sides do not determine one base")
    base_name = next(iter(base_candidates))
    base_vertices = set(base_name)
    inline_bases = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(rf"{base_name}\s*=", item)
    ]
    visible_base = re.search(
        rf"\b{base_name}\s*=\s*((?:\d+(?:\{{,\}}\d+|[.,]\d+)?)?"
        r"\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    base_latex = (
        inline_bases[0]
        if len(inline_bases) == 1
        else visible_base.group(1)
        if not inline_bases and visible_base is not None
        else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give exactly one base length")
    sine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\sin\s*[ABC]{3}\s*=", item)
    ]
    if len(sine_assignments) != 1:
        raise IsoscelesTrianglePlanError(
            "condition must give one sine of a named base angle"
        )
    sine_match = re.match(r"\\sin\s*([ABC]{3})\s*=\s*(.+)", sine_assignments[0])
    if sine_match is None:
        raise IsoscelesTrianglePlanError("sine assignment is malformed")
    angle_name, sine_latex = sine_match.groups()
    angle_vertex = angle_name[1]
    if angle_vertex not in base_vertices:
        raise IsoscelesTrianglePlanError("given angle must be a base angle")
    other_base_vertex = next(iter(base_vertices - {angle_vertex}))
    if not re.search(rf"\b{angle_vertex}H\b[^.]*высот", formula, re.IGNORECASE) and not re.search(
        rf"высот[^.]*\b{angle_vertex}H\b", formula, re.IGNORECASE
    ):
        raise IsoscelesTrianglePlanError(
            "condition must declare the altitude from the given base-angle vertex"
        )
    request = _request_text(condition_html)
    if re.findall(r"\b([ABC]H)\b", request) != [f"{other_base_vertex}H"]:
        raise IsoscelesTrianglePlanError(
            "condition must request the adjacent projection segment"
        )
    base = _parse_positive_value(base_latex)
    sine = _parse_positive_value(sine_latex)
    cosine_squared = sp.simplify(1 - sine**2)
    if cosine_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle sine must be less than one")
    cosine = sp.sqrt(cosine_squared)
    answer = _answer_text(base * cosine)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(str(solution.get("html") or ""))
    transformations = list(
        _condition_image_repairs(content, parent_solution_assets, group_key="27321")
    )
    if solution_missing:
        solution_html = (
            '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            'равнобедренный, поэтому углы при его основании равны. Следовательно,</p>'
            '<center><p><span data-inline-latex="'
            + f"{other_base_vertex}H={base_name}\\cos \\angle "
            + f"{angle_vertex}{other_base_vertex}H={base_name}\\cos \\angle {angle_name}="
            + f"{base_name}\\sqrt{{1-\\sin^{{2}} \\angle {angle_name}}}="
            + rf"{_latex_number(base)}\sqrt{{1-({sine_latex})^{{2}}}}="
            + answer.replace(",", "{,}")
            + '"></span>.</p></center>'
        )
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                solution_html,
            )
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_group_27322_repair_plan(
    context: dict[str, Any],
    *,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the base-and-cosine to opposite-side altitude repair for 27322."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    equal_match = re.search(r"\b(AB|AC|BC)\s*=\s*(AB|AC|BC)\b", formula)
    if equal_match is None or equal_match.group(1) == equal_match.group(2):
        raise IsoscelesTrianglePlanError("condition must state two equal sides")
    base_candidates = {"AB", "AC", "BC"} - {
        equal_match.group(1),
        equal_match.group(2),
    }
    if len(base_candidates) != 1:
        raise IsoscelesTrianglePlanError("equal sides do not determine one base")
    base_name = next(iter(base_candidates))
    base_vertices = set(base_name)
    inline_bases = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(rf"{base_name}\s*=", item)
    ]
    visible_base = re.search(
        rf"\b{base_name}\s*=\s*((?:\d+(?:\{{,\}}\d+|[.,]\d+)?)?"
        r"\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    base_latex = (
        inline_bases[0]
        if len(inline_bases) == 1
        else visible_base.group(1)
        if not inline_bases and visible_base is not None
        else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give exactly one base length")
    cosine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\cos\s*(?:\\angle\s*)?[ABC]{3}\s*=", item)
    ]
    if len(cosine_assignments) != 1:
        raise IsoscelesTrianglePlanError(
            "condition must give one cosine of a named base angle"
        )
    cosine_match = re.match(
        r"\\cos\s*(?:\\angle\s*)?([ABC]{3})\s*=\s*(.+)",
        cosine_assignments[0],
    )
    if cosine_match is None:
        raise IsoscelesTrianglePlanError("cosine assignment is malformed")
    angle_name, cosine_latex = cosine_match.groups()
    angle_vertex = angle_name[1]
    if angle_vertex not in base_vertices:
        raise IsoscelesTrianglePlanError("given angle must be a base angle")
    request = _request_text(condition_html)
    if re.findall(r"\b([ABC]H)\b", request) != [f"{angle_vertex}H"]:
        raise IsoscelesTrianglePlanError(
            "condition must request the altitude from the given base-angle vertex"
        )
    base = _parse_positive_value(base_latex)
    cosine = _parse_positive_value(cosine_latex)
    sine_squared = sp.simplify(1 - cosine**2)
    if sine_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle cosine must be less than one")
    sine = sp.sqrt(sine_squared)
    answer = _answer_text(base * sine)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(str(solution.get("html") or ""))
    transformations = list(
        _condition_image_repairs(content, parent_solution_assets, group_key="27322")
    )
    if solution_missing:
        other_base_vertex = next(iter(base_vertices - {angle_vertex}))
        solution_html = (
            '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            'равнобедренный, поэтому углы при его основании равны. Тогда</p>'
            '<center><p><span data-inline-latex="'
            + f"{angle_vertex}H={base_name}\\sin \\angle "
            + f"{angle_vertex}{other_base_vertex}H={base_name}\\sin \\angle {angle_name}="
            + f"{base_name}\\sqrt{{1-\\cos^{{2}} \\angle {angle_name}}}="
            + rf"{_latex_number(base)}\sqrt{{1-({cosine_latex})^{{2}}}}="
            + answer.replace(",", "{,}")
            + '"></span>.</p></center>'
        )
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                solution_html,
            )
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_group_27323_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the direct base-cosine projection repair for group 27323."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if re.search(r"\bAC\s*=\s*BC\b", formula) is None:
        raise IsoscelesTrianglePlanError("condition must state AC=BC")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    request = _request_text(condition_html)
    if re.findall(r"\b([ABC]H)\b", request) != ["BH"]:
        raise IsoscelesTrianglePlanError("condition must request BH")
    inline_bases = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(r"AB\s*=", item)
    ]
    visible_base = re.search(
        r"\bAB\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    base_latex = (
        inline_bases[0]
        if len(inline_bases) == 1
        else visible_base.group(1)
        if not inline_bases and visible_base is not None
        else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give exactly one AB length")
    cosine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\cos\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(cosine_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly cos BAC")
    cosine_latex = cosine_assignments[0].split("=", 1)[1].strip()
    base = _parse_positive_value(base_latex)
    cosine = _parse_positive_value(cosine_latex)
    if cosine >= 1:
        raise IsoscelesTrianglePlanError("base-angle cosine must be less than one")
    answer = _answer_text(base * cosine)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому углы при его основании равны. Тогда</p>'
        '<center><p><span data-inline-latex="'
        r"BH=AB\cos \angle ABH=AB\cos \angle BAC="
        + rf"{_latex_number(base)}\cdot {cosine_latex}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27324_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the base-and-tangent to opposite-side altitude repair for 27324."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if re.search(r"\bAC\s*=\s*BC\b", formula) is None:
        raise IsoscelesTrianglePlanError("condition must state AC=BC")
    if re.findall(r"\b([ABC]H)\b", _request_text(condition_html)) != ["AH"]:
        raise IsoscelesTrianglePlanError("condition must request AH")
    inline_bases = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(r"AB\s*=", item)
    ]
    visible_base = re.search(
        r"\bAB\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    base_latex = (
        inline_bases[0]
        if len(inline_bases) == 1
        else visible_base.group(1)
        if not inline_bases and visible_base is not None
        else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give exactly one AB length")
    tangent_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\tg\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(tangent_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly tg BAC")
    tangent_latex = tangent_assignments[0].split("=", 1)[1].strip()
    base = _parse_positive_value(base_latex)
    tangent = _parse_positive_value(tangent_latex)
    answer = _answer_text(base * tangent / sp.sqrt(1 + tangent**2))
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому углы при его основании равны. Последовательно получаем:</p>'
        '<center><p><span data-inline-latex="'
        r"AH=AB\sin \angle ABH=AB\sin \angle ABC="
        r"AB\sqrt{\frac{1}{1+\ctg^{2} \angle ABC}}="
        + rf"{_latex_number(base)}\sqrt{{\frac{{1}}{{1+\frac{{1}}{{({tangent_latex})^{{2}}}}}}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27325_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the base-and-tangent to adjacent projection repair for 27325."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if re.search(r"\bAC\s*=\s*BC\b", formula) is None:
        raise IsoscelesTrianglePlanError("condition must state AC=BC")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if re.findall(r"\b([ABC]H)\b", _request_text(condition_html)) != ["BH"]:
        raise IsoscelesTrianglePlanError("condition must request BH")
    inline_bases = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(r"AB\s*=", item)
    ]
    visible_base = re.search(
        r"\bAB\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    base_latex = (
        inline_bases[0]
        if len(inline_bases) == 1
        else visible_base.group(1)
        if not inline_bases and visible_base is not None
        else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give exactly one AB length")
    tangent_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\tg\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(tangent_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly tg BAC")
    tangent_latex = tangent_assignments[0].split("=", 1)[1].strip()
    base = _parse_positive_value(base_latex)
    tangent = _parse_positive_value(tangent_latex)
    answer = _answer_text(base / sp.sqrt(1 + tangent**2))
    solution_html = (
        '<p>Найдём <span data-inline-latex="BH"></span>:</p>'
        '<center><p><span data-inline-latex="'
        r"BH=AB\cos \angle ABH=AB\cos \angle BAC="
        r"AB\sqrt{\frac{1}{1+\tg^{2} \angle BAC}}="
        + rf"{_latex_number(base)}\sqrt{{\frac{{1}}{{1+({tangent_latex})^{{2}}}}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27326_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-sine to side-altitude repair for 27326."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if re.findall(r"\b([ABC]H)\b", _request_text(condition_html)) != ["AH"]:
        raise IsoscelesTrianglePlanError("condition must request AH")
    side_match = re.search(
        r"\bAC\s*=\s*BC\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?"
        r"\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    side_latex = side_match.group(1) if side_match is not None else ""
    if not side_latex and re.search(
        r"равно.*бедрен.*основан.*\bAB\b.*боков.*сторон.*равна",
        formula,
        re.IGNORECASE,
    ):
        standalone_values: list[str] = []
        for item in _inline_formulas(condition_html):
            if "=" in item:
                continue
            try:
                _parse_positive_value(item.strip())
            except IsoscelesTrianglePlanError:
                continue
            standalone_values.append(item.strip())
        if len(standalone_values) == 1:
            side_latex = standalone_values[0]
    if not side_latex:
        raise IsoscelesTrianglePlanError(
            "condition must give the equal side AC=BC"
        )
    sine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\sin\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(sine_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly sin BAC")
    sine_latex = sine_assignments[0].split("=", 1)[1].strip()
    side = _parse_positive_value(side_latex)
    sine = _parse_positive_value(sine_latex)
    cosine_squared = sp.simplify(1 - sine**2)
    if cosine_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle sine must be less than one")
    cosine = sp.sqrt(cosine_squared)
    answer = _answer_text(2 * side * sine * cosine)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому углы при его основании равны, а высота из '
        '<span data-inline-latex="C"></span> делит основание пополам. Тогда</p>'
        '<center><p><span data-inline-latex="'
        r"AH=AB\sin \angle ABH=AB\sin \angle BAC="
        r"2AC\cos \angle BAC\sin \angle BAC="
        r"2AC\sin \angle BAC\sqrt{1-\sin^{2} \angle BAC}="
        + rf"2\cdot {_latex_number(side)}\cdot {sine_latex}"
        + rf"\sqrt{{1-({sine_latex})^{{2}}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27327_repair_plan(
    context: dict[str, Any],
    *,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the equal-side-and-sine to external projection repair for 27327."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    side_match = re.search(
        r"\bAC\s*=\s*BC\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?"
        r"\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if re.findall(r"\b([ABC]H)\b", _request_text(condition_html)) != ["BH"]:
        raise IsoscelesTrianglePlanError("condition must request BH")
    sine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\sin\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(sine_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly sin BAC")
    side_latex = side_match.group(1)
    sine_latex = sine_assignments[0].split("=", 1)[1].strip()
    side = _parse_positive_value(side_latex)
    sine = _parse_positive_value(sine_latex)
    cosine_squared = sp.simplify(1 - sine**2)
    if cosine_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle sine must be less than one")
    answer = _answer_text(2 * side * cosine_squared)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(str(solution.get("html") or ""))
    transformations = list(
        _condition_image_repairs(content, parent_solution_assets, group_key="27327")
    )
    if solution_missing:
        solution_html = (
            '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            'равнобедренный, поэтому углы при его основании равны, а высота из '
            '<span data-inline-latex="C"></span> делит основание пополам. Имеем:</p>'
            '<center><p><span data-inline-latex="'
            r"BH=AB\cos \angle ABH=AB\cos \angle BAC="
            r"2AC\cos^{2} \angle BAC=2AC(1-\sin^{2} \angle BAC)="
            + rf"2\cdot {_latex_number(side)}\cdot (1-({sine_latex})^{{2}})="
            + answer.replace(",", "{,}")
            + '"></span>.</p></center>'
        )
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                solution_html,
            )
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_group_27328_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-cosine to side-altitude repair for 27328."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if re.findall(r"\b([ABC]H)\b", _request_text(condition_html)) != ["AH"]:
        raise IsoscelesTrianglePlanError("condition must request AH")
    side_match = re.search(
        r"\bAC\s*=\s*BC\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?"
        r"\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC")
    cosine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\cos\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(cosine_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly cos BAC")
    side_latex = side_match.group(1)
    cosine_latex = cosine_assignments[0].split("=", 1)[1].strip()
    side = _parse_positive_value(side_latex)
    cosine = _parse_positive_value(cosine_latex)
    sine_squared = sp.simplify(1 - cosine**2)
    if sine_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle cosine must be less than one")
    answer = _answer_text(2 * side * cosine * sp.sqrt(sine_squared))
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому углы при его основании равны, а высота из '
        '<span data-inline-latex="C"></span> делит основание пополам. Тогда</p>'
        '<center><p><span data-inline-latex="'
        r"AH=AB\sin \angle ABH=AB\sin \angle BAC="
        r"2AC\cos \angle BAC\sin \angle BAC="
        r"2AC\cos \angle BAC\sqrt{1-\cos^{2} \angle BAC}="
        + rf"2\cdot {_latex_number(side)}\cdot {cosine_latex}"
        + rf"\sqrt{{1-({cosine_latex})^{{2}}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27329_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-cosine to external projection repair for 27329."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    side_match = re.search(
        r"\bAC\s*=\s*BC\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?"
        r"\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if re.findall(r"\b([ABC]H)\b", _request_text(condition_html)) != ["BH"]:
        raise IsoscelesTrianglePlanError("condition must request BH")
    cosine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\cos\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(cosine_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly cos BAC")
    side_latex = side_match.group(1)
    cosine_latex = cosine_assignments[0].split("=", 1)[1].strip()
    side = _parse_positive_value(side_latex)
    cosine = _parse_positive_value(cosine_latex)
    if sp.simplify(1 - cosine).is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle cosine must be less than one")
    answer = _answer_text(2 * side * cosine**2)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому углы при его основании равны, а высота из '
        '<span data-inline-latex="C"></span> делит основание пополам. Тогда</p>'
        '<center><p><span data-inline-latex="'
        r"BH=AB\cos \angle ABH=AB\cos \angle BAC="
        r"2AC\cos^{2} \angle BAC="
        + rf"2\cdot {_latex_number(side)}\cdot ({cosine_latex})^{{2}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27330_repair_plan(
    context: dict[str, Any],
    *,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the altitude-and-side to base-angle sine repair for 27330."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    first_orientation = re.search(r"\bAC\s*=\s*BC\b", formula) is not None
    second_orientation = re.search(r"\bAB\s*=\s*BC\b", formula) is not None
    if first_orientation == second_orientation:
        raise IsoscelesTrianglePlanError(
            "condition must give exactly AC=BC or AB=BC"
        )
    base_name = "AB" if first_orientation else "AC"
    altitude_name = "AH" if first_orientation else "CH"
    requested_angle = "A" if first_orientation else "C"
    long_angle = "BAC" if first_orientation else "ACB"
    base_match = re.search(rf"\b{base_name}\s*=\s*{number}", formula)
    altitude_match = re.search(
        rf"\b{altitude_name}\s*(?:=|равна)\s*{number}",
        formula,
        re.IGNORECASE,
    )
    if base_match is None or altitude_match is None:
        raise IsoscelesTrianglePlanError(
            f"condition must give {base_name} and altitude {altitude_name}"
        )
    request = _request_text(condition_html)
    if not re.search(
        rf"(?:синус(?:\s+угла)?|\\sin)\s*(?:\\angle\s*)?(?:{requested_angle}|{long_angle})\b",
        request,
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError(f"condition must request sin {requested_angle}")
    base_latex = base_match.group(1)
    altitude_latex = altitude_match.group(1)
    base = _parse_positive_value(base_latex)
    altitude = _parse_positive_value(altitude_latex)
    sine = sp.simplify(altitude / base)
    if sp.simplify(1 - sine).is_positive is not True:
        raise IsoscelesTrianglePlanError(
            f"{altitude_name} must be less than {base_name}"
        )
    answer = _answer_text(sine)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(str(solution.get("html") or ""))
    transformations = list(
        _condition_image_repairs(content, parent_solution_assets, group_key="27330")
        if first_orientation
        else ()
    )
    if solution_missing:
        relation = (
            r"\sin \angle BAC=\sin \angle ABH=\frac{AH}{AB}="
            if first_orientation
            else r"\sin \angle ACB=\sin \angle BAC=\frac{CH}{AC}="
        )
        solution_html = (
            '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            'равнобедренный, поэтому углы при его основании равны. Тогда</p>'
            '<center><p><span data-inline-latex="'
            + relation
            + rf"\frac{{{_latex_number(altitude)}}}{{{_latex_number(base)}}}="
            + answer.replace(",", "{,}")
            + '"></span>.</p></center>'
        )
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                solution_html,
            )
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_group_27331_repair_plan(
    context: dict[str, Any],
    *,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the altitude-and-side to base-angle cosine repair for 27331."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must give AC=BC")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    base_match = re.search(rf"\bAB\s*=\s*{number}", formula)
    altitude_match = re.search(
        rf"\bAH\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE
    )
    projection_match = re.search(rf"\bBH\s*=\s*{number}", formula)
    cosine_variant = base_match is not None and projection_match is None
    sine_variant = base_match is None and projection_match is not None
    if altitude_match is None or cosine_variant == sine_variant:
        raise IsoscelesTrianglePlanError(
            "condition must give AH and exactly one of AB or BH"
        )
    request = _request_text(condition_html)
    altitude = _parse_positive_value(altitude_match.group(1))
    if cosine_variant:
        if not re.search(
            r"(?:косинус(?:\s+угла)?|\\cos)\s*(?:\\angle\s*)?(?:A|BAC)\b",
            request,
            re.IGNORECASE,
        ):
            raise IsoscelesTrianglePlanError("AB/AH variant must request cos A")
        base = _parse_positive_value(base_match.group(1))
        projection_squared = sp.simplify(base**2 - altitude**2)
        if projection_squared.is_positive is not True:
            raise IsoscelesTrianglePlanError("AH must be less than AB")
        projection = sp.sqrt(projection_squared)
        answer_value = sp.simplify(projection / base)
    else:
        if not re.search(
            r"(?:синус(?:\s+угла)?|\\sin)\s*(?:\\angle\s*)?(?:A|BAC)\b",
            request,
            re.IGNORECASE,
        ):
            raise IsoscelesTrianglePlanError("AH/BH variant must request sin A")
        projection = _parse_positive_value(projection_match.group(1))
        base = sp.sqrt(altitude**2 + projection**2)
        answer_value = sp.simplify(altitude / base)
    answer = _answer_text(answer_value)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(str(solution.get("html") or ""))
    transformations = list(
        _condition_image_repairs(content, parent_solution_assets, group_key="27331")
    )
    if solution_missing:
        base_latex = _latex_number(base)
        altitude_latex = _latex_number(altitude)
        projection_latex = _latex_number(projection)
        relation = (
            r"\cos \angle BAC=\cos \angle ABH=\frac{BH}{AB}="
            r"\frac{\sqrt{AB^{2}-AH^{2}}}{AB}="
            + rf"\frac{{\sqrt{{({base_latex})^{{2}}-({altitude_latex})^{{2}}}}}}{{{base_latex}}}="
            + rf"\frac{{{projection_latex}}}{{{base_latex}}}="
            if cosine_variant
            else r"AB=\sqrt{AH^{2}+BH^{2}}="
            + rf"\sqrt{{({altitude_latex})^{{2}}+({projection_latex})^{{2}}}}={base_latex},\quad "
            + r"\sin \angle BAC=\sin \angle ABH=\frac{AH}{AB}="
            + rf"\frac{{{altitude_latex}}}{{{base_latex}}}="
        )
        solution_html = (
            '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            'равнобедренный, поэтому углы при его основании равны. Тогда</p>'
            '<center><p><span data-inline-latex="'
            + relation
            + answer.replace(",", "{,}")
            + '"></span>.</p></center>'
        )
        transformations.append(
            _section_transformation(
                solution, "solution", "Решение", solution_html
            )
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_group_27345_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse equal-side altitude-to-vertex-sine repair for 27345."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"тупо.*уголь", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an obtuse triangle")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    side_match = re.search(rf"\bAC\s*=\s*BC\s*=\s*{number}", formula)
    altitude_match = re.search(
        rf"\bAH\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE
    )
    if side_match is None or altitude_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and altitude AH")
    request = _request_text(condition_html)
    if not re.search(
        r"(?:синус(?:\s+угла)?|\\sin)\s*(?:\\angle\s*)?ACB\b",
        request,
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request sin ACB")
    side = _parse_positive_value(side_match.group(1))
    altitude = _parse_positive_value(altitude_match.group(1))
    if sp.simplify(side - altitude).is_positive is not True:
        raise IsoscelesTrianglePlanError("AH must be less than AC")
    answer = _answer_text(sp.simplify(altitude / side))
    solution_html = (
        '<p>Синусы смежных углов равны, поэтому</p>'
        '<center><p><span data-inline-latex="'
        r"\sin \angle ACB=\sin \angle ACH=\frac{AH}{AC}="
        + rf"\frac{{{_latex_number(altitude)}}}{{{_latex_number(side)}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27346_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse equal-side altitude-to-vertex-cosine repair for 27346."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"тупо.*уголь", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an obtuse triangle")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    first_side = re.search(rf"\bAC\s*=\s*BC\s*=\s*{number}", formula)
    second_equal = re.search(r"\bAB\s*=\s*BC\b", formula)
    second_side = re.search(rf"\bAB\s*=\s*{number}", formula)
    first_orientation = first_side is not None and second_equal is None
    second_orientation = first_side is None and second_equal is not None and second_side is not None
    if first_orientation == second_orientation:
        raise IsoscelesTrianglePlanError("condition has an unsupported equal-side orientation")
    altitude_name = "AH" if first_orientation else "CH"
    requested_angle = "ACB" if first_orientation else "ABC"
    altitude_match = re.search(
        rf"\b{altitude_name}\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE
    )
    if altitude_match is None:
        raise IsoscelesTrianglePlanError(f"condition must give altitude {altitude_name}")
    if not re.search(
        rf"(?:косинус(?:\s+угла)?|\\cos)\s*(?:\\angle\s*)?{requested_angle}\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError(f"condition must request cos {requested_angle}")
    side = _parse_positive_value(
        first_side.group(1) if first_orientation else second_side.group(1)
    )
    altitude = _parse_positive_value(altitude_match.group(1))
    projection_squared = sp.simplify(side**2 - altitude**2)
    if projection_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("altitude must be less than the equal side")
    projection = sp.sqrt(projection_squared)
    answer = _answer_text(-sp.simplify(projection / side))
    relation = (
        r"\cos \angle ACB=-\cos \angle ACH=-\frac{HC}{AC}="
        r"-\frac{\sqrt{AC^{2}-AH^{2}}}{AC}="
        if first_orientation
        else r"\cos \angle ABC=-\cos \angle CBH=-\frac{BH}{BC}="
        r"-\frac{\sqrt{BC^{2}-CH^{2}}}{BC}="
    )
    side_latex = _latex_number(side)
    altitude_latex = _latex_number(altitude)
    solution_html = (
        '<p>Косинусы смежных углов противоположны, поэтому</p>'
        '<center><p><span data-inline-latex="'
        + relation
        + rf"-\frac{{\sqrt{{({side_latex})^{{2}}-({altitude_latex})^{{2}}}}}}{{{side_latex}}}="
        + rf"-\frac{{{_latex_number(projection)}}}{{{side_latex}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27347_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse equal-side altitude-to-vertex-tangent repair for 27347."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"тупо.*уголь", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an obtuse triangle")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    side_match = re.search(rf"\bAC\s*=\s*BC\s*=\s*{number}", formula)
    altitude_match = re.search(
        rf"\bAH\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE
    )
    if side_match is None or altitude_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and altitude AH")
    if not re.search(
        r"(?:тангенс(?:\s+угла)?|\\tg)\s*(?:\\angle\s*)?ACB\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request tg ACB")
    side = _parse_positive_value(side_match.group(1))
    altitude = _parse_positive_value(altitude_match.group(1))
    projection_squared = sp.simplify(side**2 - altitude**2)
    if projection_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("AH must be less than AC")
    projection = sp.sqrt(projection_squared)
    answer = _answer_text(-sp.simplify(altitude / projection))
    side_latex = _latex_number(side)
    altitude_latex = _latex_number(altitude)
    solution_html = (
        '<p>Используем свойство смежных углов, формулу приведения, '
        'определение тангенса и теорему Пифагора:</p>'
        '<center><p><span data-inline-latex="'
        r"\tg \angle ACB=\tg (\pi-\angle ACH)=-\tg \angle ACH="
        r"-\frac{AH}{HC}=-\frac{AH}{\sqrt{AC^{2}-AH^{2}}}="
        + rf"-\frac{{{altitude_latex}}}{{\sqrt{{({side_latex})^{{2}}-({altitude_latex})^{{2}}}}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27349_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse equal-side projection-to-vertex-cosine repair for 27349."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"тупо.*уголь", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an obtuse triangle")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    side_match = re.search(rf"\bAC\s*=\s*BC\s*=\s*{number}", formula)
    projection_match = re.search(rf"\bCH\s*=\s*{number}", formula)
    if side_match is None or projection_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and CH")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if not re.search(
        r"(?:косинус(?:\s+угла)?|\\cos)\s*(?:\\angle\s*)?ACB\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request cos ACB")
    side = _parse_positive_value(side_match.group(1))
    projection = _parse_positive_value(projection_match.group(1))
    if sp.simplify(side - projection).is_positive is not True:
        raise IsoscelesTrianglePlanError("CH must be less than AC")
    answer = _answer_text(-sp.simplify(projection / side))
    solution_html = (
        '<p>Косинусы смежных углов противоположны, поэтому</p>'
        '<center><p><span data-inline-latex="'
        r"\cos \angle ACB=\cos (\pi-\angle ACH)=-\cos \angle ACH="
        r"-\frac{HC}{AC}="
        + rf"-\frac{{{_latex_number(projection)}}}{{{_latex_number(side)}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27350_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse equal-side projection-to-vertex-tangent repair for 27350."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"тупо.*уголь", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an obtuse triangle")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    side_match = re.search(rf"\bAC\s*=\s*BC\s*=\s*{number}", formula)
    projection_match = re.search(rf"\bCH\s*=\s*{number}", formula)
    if side_match is None or projection_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and CH")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if not re.search(
        r"(?:тангенс(?:\s+угла)?|\\tg)\s*(?:\\angle\s*)?ACB\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request tg ACB")
    side = _parse_positive_value(side_match.group(1))
    projection = _parse_positive_value(projection_match.group(1))
    altitude_squared = sp.simplify(side**2 - projection**2)
    if altitude_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("CH must be less than AC")
    altitude = sp.sqrt(altitude_squared)
    answer = _answer_text(-sp.simplify(altitude / projection))
    solution_html = (
        '<p>Используем свойство смежных углов, формулу приведения, '
        'определение тангенса и теорему Пифагора:</p>'
        '<center><p><span data-inline-latex="'
        r"\tg \angle ACB=\tg (180^{\circ}-\angle ACH)=-\tg \angle ACH="
        r"-\frac{AH}{CH}=-\frac{\sqrt{AC^{2}-CH^{2}}}{CH}="
        + rf"-\frac{{\sqrt{{({_latex_number(side)})^{{2}}-({_latex_number(projection)})^{{2}}}}}}{{{_latex_number(projection)}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27351_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse altitude/projection-to-vertex-sine repair for 27351."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"тупо.*уголь", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an obtuse triangle")
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    altitude_match = re.search(rf"\bAH\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE)
    projection_match = re.search(rf"\bCH\s*=\s*{number}", formula)
    if altitude_match is None or projection_match is None:
        raise IsoscelesTrianglePlanError("condition must give altitude AH and projection CH")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if not re.search(
        r"(?:синус(?:\s+угла)?|\\sin)\s*(?:\\angle\s*)?ACB\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request sin ACB")
    altitude = _parse_positive_value(altitude_match.group(1))
    projection = _parse_positive_value(projection_match.group(1))
    side = sp.sqrt(sp.simplify(altitude**2 + projection**2))
    answer = _answer_text(sp.simplify(altitude / side))
    solution_html = (
        '<p>По теореме Пифагора в <span data-inline-latex="\\triangle ACH"></span>:</p>'
        '<center><p><span data-inline-latex="'
        r"AC=\sqrt{AH^{2}+CH^{2}}="
        + rf"\sqrt{{({_latex_number(altitude)})^{{2}}+({_latex_number(projection)})^{{2}}}}={_latex_number(side)}"
        + '"></span>.</p></center>'
        '<p>Синусы смежных углов равны, поэтому</p>'
        '<center><p><span data-inline-latex="'
        r"\sin \angle ACB=\sin (180^{\circ}-\angle ACH)=\sin \angle ACH="
        r"\frac{AH}{AC}="
        + rf"\frac{{{_latex_number(altitude)}}}{{{_latex_number(side)}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27352_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse altitude/projection-to-vertex-cosine repair for 27352."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"тупо.*уголь", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an obtuse triangle")
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    altitude_match = re.search(rf"\bAH\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE)
    projection_match = re.search(rf"\bCH\s*=\s*{number}", formula)
    if altitude_match is None or projection_match is None:
        raise IsoscelesTrianglePlanError("condition must give altitude AH and projection CH")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if not re.search(
        r"(?:косинус(?:\s+угла)?|\\cos)\s*(?:\\angle\s*)?ACB\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request cos ACB")
    altitude = _parse_positive_value(altitude_match.group(1))
    projection = _parse_positive_value(projection_match.group(1))
    side = sp.sqrt(sp.simplify(altitude**2 + projection**2))
    answer = _answer_text(-sp.simplify(projection / side))
    solution_html = (
        '<p>По теореме Пифагора в <span data-inline-latex="\\triangle ACH"></span>:</p>'
        '<center><p><span data-inline-latex="'
        r"AC=\sqrt{AH^{2}+CH^{2}}="
        + rf"\sqrt{{({_latex_number(altitude)})^{{2}}+({_latex_number(projection)})^{{2}}}}={_latex_number(side)}"
        + '"></span>.</p></center>'
        '<p>Косинусы смежных углов противоположны, поэтому</p>'
        '<center><p><span data-inline-latex="'
        r"\cos \angle ACB=\cos (180^{\circ}-\angle ACH)=-\cos \angle ACH="
        r"-\frac{CH}{AC}="
        + rf"-\frac{{{_latex_number(projection)}}}{{{_latex_number(side)}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27353_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse altitude/projection-to-vertex-tangent repair for 27353."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"тупо.*уголь", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an obtuse triangle")
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    altitude_match = re.search(rf"\bAH\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE)
    projection_match = re.search(rf"\bCH\s*=\s*{number}", formula)
    if altitude_match is None or projection_match is None:
        raise IsoscelesTrianglePlanError("condition must give altitude AH and projection CH")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if not re.search(
        r"(?:тангенс(?:\s+угла)?|\\tg)\s*(?:\\angle\s*)?ACB\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request tg ACB")
    altitude = _parse_positive_value(altitude_match.group(1))
    projection = _parse_positive_value(projection_match.group(1))
    answer = _answer_text(-sp.simplify(altitude / projection))
    solution_html = (
        '<p>Тангенсы смежных углов противоположны, поэтому</p>'
        '<center><p><span data-inline-latex="'
        r"\tg \angle ACB=\tg (180^{\circ}-\angle ACH)=-\tg \angle ACH="
        r"-\frac{AH}{CH}="
        + rf"-\frac{{{_latex_number(altitude)}}}{{{_latex_number(projection)}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27589_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the 30-degree vertex-angle area repair for group 27589."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    request = _request_text(condition_html)
    if not re.search(r"площад", request, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the triangle area")
    if not re.search(r"(?:30\s*(?:\^\{?\\circ\}?|°)|угол\s+C\s+равен\s+30)", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must give a 30-degree vertex angle")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    named_side = re.search(rf"\bAC\s*=\s*BC\s*=\s*{number}", formula)
    verbal_side = re.search(
        rf"боков[^.]*сторон[^.]*равна\s*{number}",
        formula,
        re.IGNORECASE,
    )
    side_latex = (
        named_side.group(1)
        if named_side is not None
        else verbal_side.group(1)
        if verbal_side is not None
        else ""
    )
    if not side_latex:
        raise IsoscelesTrianglePlanError("condition must give the equal side length")
    side = _parse_positive_value(side_latex)
    answer = _answer_text(sp.simplify(side**2 / 4))
    solution_html = (
        '<p>Площадь треугольника равна половине произведения двух сторон '
        'на синус угла между ними. Поэтому</p>'
        '<center><p><span data-inline-latex="'
        r"S=\frac{1}{2}a^{2}\sin 30^{\circ}="
        + rf"\frac{{1}}{{2}}\cdot ({_latex_number(side)})^{{2}}\cdot \frac{{1}}{{2}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27590_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the 150-degree vertex-angle area repair for group 27590."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html)
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    if not re.search(r"площад", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the triangle area")
    if not re.search(r"150\s*(?:\^\{?\\circ\}?|°)", formula):
        raise IsoscelesTrianglePlanError("condition must give a 150-degree vertex angle")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    side_match = re.search(
        rf"боков[^.]*сторон[^.]*равна\s*{number}",
        formula,
        re.IGNORECASE,
    )
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must give the equal side length")
    side = _parse_positive_value(side_match.group(1))
    answer = _answer_text(sp.simplify(side**2 / 4))
    solution_html = (
        '<p>Площадь треугольника равна половине произведения двух сторон '
        'на синус угла между ними. Поэтому</p>'
        '<center><p><span data-inline-latex="'
        r"S=\frac{1}{2}a^{2}\sin 150^{\circ}="
        r"\frac{1}{2}a^{2}\sin 30^{\circ}="
        + rf"\frac{{1}}{{2}}\cdot ({_latex_number(side)})^{{2}}\cdot \frac{{1}}{{2}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27619_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the side-and-base-to-area repair for group 27619."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html)
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    if not re.search(r"площад", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the triangle area")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    side_match = re.search(
        rf"боков[^.]*сторон[^.]*равна\s*{number}",
        formula,
        re.IGNORECASE,
    )
    base_match = re.search(
        rf"основан[^.]*равно\s*{number}",
        formula,
        re.IGNORECASE,
    )
    if side_match is None or base_match is None:
        raise IsoscelesTrianglePlanError("condition must give the equal side and base lengths")
    side = _parse_positive_value(side_match.group(1))
    base = _parse_positive_value(base_match.group(1))
    half_base = sp.simplify(base / 2)
    radicand = sp.simplify(side**2 - half_base**2)
    if radicand <= 0:
        raise IsoscelesTrianglePlanError("side and base do not form a nondegenerate triangle")
    altitude = sp.sqrt(radicand)
    area = sp.simplify(base * altitude / 2)
    answer = _answer_text(area)
    solution_html = (
        '<p>Высота равнобедренного треугольника, проведённая к основанию, '
        'делит основание пополам. По теореме Пифагора найдём высоту:</p>'
        '<center><p><span data-inline-latex="'
        r"h=\sqrt{a^{2}-\left(\frac{b}{2}\right)^{2}}="
        + rf"\sqrt{{({_latex_number(side)})^{{2}}-({_latex_number(half_base)})^{{2}}}}={_latex_number(altitude)}"
        + '"></span>.</p></center>'
        '<p>Тогда площадь треугольника равна</p>'
        '<center><p><span data-inline-latex="'
        r"S=\frac{1}{2}bh="
        + rf"\frac{{1}}{{2}}\cdot {_latex_number(base)}\cdot {_latex_number(altitude)}={answer.replace(',', '{,}') }"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27620_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the 30-degree area-to-equal-side repair for group 27620."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html)
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    if not re.search(r"30\s*(?:\^\{?\\circ\}?|°)", formula):
        raise IsoscelesTrianglePlanError("condition must give a 30-degree vertex angle")
    request = _request_text(condition_html)
    if not re.search(r"боков", request, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the equal side")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    area_match = re.search(rf"площад[^.]*равна\s*{number}", formula, re.IGNORECASE)
    if area_match is None:
        raise IsoscelesTrianglePlanError("condition must give the triangle area")
    area = _parse_positive_value(area_match.group(1))
    side = sp.simplify(2 * sp.sqrt(area))
    answer = _answer_text(side)
    solution_html = (
        '<p>Площадь треугольника равна половине произведения двух сторон '
        'на синус угла между ними:</p>'
        '<center><p><span data-inline-latex="'
        r"S=\frac{1}{2}a^{2}\sin 30^{\circ}=\frac{a^{2}}{4}"
        + '"></span>.</p></center>'
        '<p>Следовательно,</p>'
        '<center><p><span data-inline-latex="'
        + rf"a=2\sqrt{{S}}=2\sqrt{{{_latex_number(area)}}}={answer.replace(',', '{,}') }"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27621_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the 150-degree area-to-equal-side repair for group 27621."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html)
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    if not re.search(r"150\s*(?:\^\{?\\circ\}?|°)", formula):
        raise IsoscelesTrianglePlanError("condition must give a 150-degree vertex angle")
    if not re.search(r"боков", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the equal side")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    area_match = re.search(rf"площад[^.]*равна\s*{number}", formula, re.IGNORECASE)
    if area_match is None:
        raise IsoscelesTrianglePlanError("condition must give the triangle area")
    area = _parse_positive_value(area_match.group(1))
    side = sp.simplify(2 * sp.sqrt(area))
    answer = _answer_text(side)
    solution_html = (
        '<p>Площадь треугольника равна половине произведения двух сторон '
        'на синус угла между ними:</p>'
        '<center><p><span data-inline-latex="'
        r"S=\frac{1}{2}a^{2}\sin 150^{\circ}="
        r"\frac{1}{2}a^{2}\sin 30^{\circ}=\frac{a^{2}}{4}"
        + '"></span>.</p></center>'
        '<p>Следовательно,</p>'
        '<center><p><span data-inline-latex="'
        + rf"a=2\sqrt{{S}}=2\sqrt{{{_latex_number(area)}}}={answer.replace(',', '{,}') }"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27744_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side base-angle-to-vertex-angle repair for 27744."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if not (
        re.search(r"\bAC\s*=\s*BC\b", formula)
        or re.search(r"сторон[^.]*\bAC\b[^.]*\bBC\b[^.]*равны", formula, re.IGNORECASE)
    ):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    angle_match = re.search(r"угол\s+A\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)", formula, re.IGNORECASE)
    if angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give angle A in degrees")
    if not re.search(r"угол\s+C\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle C")
    angle_a = int(angle_match.group(1))
    angle_c = 180 - 2 * angle_a
    if angle_c <= 0:
        raise IsoscelesTrianglePlanError("given angle does not form a triangle")
    answer = str(angle_c)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> равнобедренный, '
        'поэтому углы при основании равны:</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle A=\angle B={angle_a}^{{\circ}}"
        + '"></span>.</p></center>'
        '<p>По сумме углов треугольника</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle C=180^{{\circ}}-\angle A-\angle B=180^{{\circ}}-2\cdot {angle_a}^{{\circ}}={angle_c}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27745_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side vertex-angle-to-base-angle repair for 27745."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if not (
        re.search(r"\bAC\s*=\s*BC\b", formula)
        or re.search(r"сторон[^.]*\bAC\b[^.]*\bBC\b[^.]*равны", formula, re.IGNORECASE)
    ):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    angle_match = re.search(r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)", formula, re.IGNORECASE)
    if angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give angle C in degrees")
    if not re.search(r"угол\s+A\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle A")
    angle_c = int(angle_match.group(1))
    angle_a = sp.Rational(180 - angle_c, 2)
    if angle_a <= 0:
        raise IsoscelesTrianglePlanError("given angle does not form a triangle")
    answer = _answer_text(angle_a)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> равнобедренный, '
        'поэтому углы при основании равны. По сумме углов треугольника</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle A=\angle B=\frac{{180^{{\circ}}-\angle C}}{{2}}="
        + rf"\frac{{180^{{\circ}}-{angle_c}^{{\circ}}}}{{2}}={_latex_number(angle_a)}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27746_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the vertex-angle-to-exterior-base-angle repair for 27746."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if not (
        re.search(r"\bAC\s*=\s*BC\b", formula)
        or re.search(r"сторон[^.]*\bAC\b[^.]*\bBC\b[^.]*равны", formula, re.IGNORECASE)
    ):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    angle_match = re.search(r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)", formula, re.IGNORECASE)
    if angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give angle C in degrees")
    request = _request_text(condition_html)
    if not re.search(r"внешн[^.]*угол\s+CBD\b", request, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request exterior angle CBD")
    angle_c = int(angle_match.group(1))
    angle_b = sp.Rational(180 - angle_c, 2)
    exterior = 180 - angle_b
    if angle_b <= 0:
        raise IsoscelesTrianglePlanError("given angle does not form a triangle")
    answer = _answer_text(exterior)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> равнобедренный, '
        'поэтому углы при основании равны:</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle B=\frac{{180^{{\circ}}-\angle C}}{{2}}="
        + rf"\frac{{180^{{\circ}}-{angle_c}^{{\circ}}}}{{2}}={_latex_number(angle_b)}^{{\circ}}"
        + '"></span>.</p></center>'
        '<p>Внешний угол <span data-inline-latex="CBD"></span> смежный с углом '
        '<span data-inline-latex="B"></span>, поэтому</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle CBD=180^{{\circ}}-\angle B=180^{{\circ}}-{_latex_number(angle_b)}^{{\circ}}={_latex_number(exterior)}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27747_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the exterior-base-angle-to-vertex-angle repair for 27747."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    exterior_match = re.search(
        r"(?:в|B)нешн[^.]*угол\s+при\s+вершин[^.]*B[^.]*равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if exterior_match is None:
        raise IsoscelesTrianglePlanError("condition must give the exterior angle at B")
    if not re.search(r"угол\s+C\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle C")
    exterior = int(exterior_match.group(1))
    angle_b = 180 - exterior
    angle_c = 180 - 2 * angle_b
    if angle_b <= 0 or angle_c <= 0:
        raise IsoscelesTrianglePlanError("given exterior angle does not form a triangle")
    answer = str(angle_c)
    solution_html = (
        '<p>Внутренний угол <span data-inline-latex="B"></span> смежный с данным внешним углом, поэтому</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle B=180^{{\circ}}-{exterior}^{{\circ}}={angle_b}^{{\circ}}"
        + '"></span>.</p></center>'
        '<p>Треугольник <span data-inline-latex="ABC"></span> равнобедренный, '
        'поэтому <span data-inline-latex="\angle A=\angle B"></span>. Тогда</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle C=180^{{\circ}}-2\angle B=180^{{\circ}}-2\cdot {angle_b}^{{\circ}}={angle_c}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27748_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the exterior-vertex-angle-to-base-angle repair for 27748."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if not re.search(r"\bAB\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AB=BC")
    exterior_match = re.search(
        r"(?:в|B)нешн[^.]*угол\s+при\s+вершин[^.]*B[^.]*равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if exterior_match is None:
        raise IsoscelesTrianglePlanError("condition must give the exterior angle at B")
    if not re.search(r"угол\s+C\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle C")
    exterior = int(exterior_match.group(1))
    angle_b = 180 - exterior
    angle_c = sp.Rational(exterior, 2)
    if angle_b <= 0:
        raise IsoscelesTrianglePlanError("given exterior angle does not form a triangle")
    answer = _answer_text(angle_c)
    solution_html = (
        '<p>Внутренний угол <span data-inline-latex="B"></span> смежный с данным внешним углом:</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle B=180^{{\circ}}-{exterior}^{{\circ}}={angle_b}^{{\circ}}"
        + '"></span>.</p></center>'
        '<p>Треугольник <span data-inline-latex="ABC"></span> равнобедренный, '
        'поэтому углы при основании равны:</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle C=\frac{{180^{{\circ}}-\angle B}}{{2}}="
        + rf"\frac{{180^{{\circ}}-{angle_b}^{{\circ}}}}{{2}}={_latex_number(angle_c)}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27750_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the larger-to-smaller-angle repair for group 27750."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html)
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    larger_match = re.search(
        r"больш[^.]*угол[^.]*равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if larger_match is None:
        raise IsoscelesTrianglePlanError("condition must give the larger angle")
    if not re.search(r"меньш[^.]*угол", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the smaller angle")
    larger = int(larger_match.group(1))
    smaller = sp.Rational(180 - larger, 2)
    if larger <= 60 or smaller <= 0:
        raise IsoscelesTrianglePlanError("given angle is not the unique larger angle")
    answer = _answer_text(smaller)
    solution_html = (
        '<p>Данный больший угол является углом при вершине. Два угла при основании '
        'равнобедренного треугольника равны, поэтому меньший угол равен</p>'
        '<center><p><span data-inline-latex="'
        + rf"\frac{{180^{{\circ}}-{larger}^{{\circ}}}}{{2}}={_latex_number(smaller)}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27754_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the angle-difference-to-smaller-angle repair for 27754."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html)
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    difference_match = re.search(
        r"один\s+угол[^.]*на\s*(\d+)\s*(?:\^\{?\\circ\}?|°)[^.]*больше\s+друг",
        formula,
        re.IGNORECASE,
    )
    if difference_match is None:
        raise IsoscelesTrianglePlanError("condition must give the angle difference")
    if not re.search(r"меньш[^.]*угол", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the smaller angle")
    difference = int(difference_match.group(1))
    smaller = sp.Rational(180 - difference, 3)
    if smaller <= 0:
        raise IsoscelesTrianglePlanError("given difference does not form a triangle")
    answer = _answer_text(smaller)
    solution_html = (
        '<p>Пусть меньший угол равен <span data-inline-latex="x^{\\circ}"></span>. '
        'Два меньших угла при основании равны, а больший угол равен '
        f'<span data-inline-latex="(x+{difference})^{{\\circ}}"></span>. По сумме углов треугольника</p>'
        '<center><p><span data-inline-latex="'
        + rf"2x+(x+{difference})=180\iff 3x={180-difference}\iff x={_latex_number(smaller)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27760_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the altitude-angle-to-vertex-angle repair for group 27760."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    if not re.search(r"\bAD\b[^.]*высот|высот[^.]*\bAD\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AD as an altitude")
    angle_match = re.search(
        r"угол\s+BAD\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give angle BAD")
    if not re.search(r"угол\s+C\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle C")
    angle_bad = int(angle_match.group(1))
    angle_b = 90 - angle_bad
    angle_c = 2 * angle_bad
    if angle_bad <= 0 or angle_b <= 0:
        raise IsoscelesTrianglePlanError("given altitude angle does not form a triangle")
    answer = str(angle_c)
    solution_html = (
        '<p>Так как <span data-inline-latex="AD"></span> — высота, '
        '<span data-inline-latex="\\triangle ABD"></span> прямоугольный. Поэтому</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle B=90^{{\circ}}-\angle BAD=90^{{\circ}}-{angle_bad}^{{\circ}}={angle_b}^{{\circ}}"
        + '"></span>.</p></center>'
        '<p>В равнобедренном <span data-inline-latex="\\triangle ABC"></span> '
        '<span data-inline-latex="\\angle A=\\angle B"></span>, следовательно,</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle C=180^{{\circ}}-2\angle B=180^{{\circ}}-2\cdot {angle_b}^{{\circ}}={angle_c}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27792_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equilateral-side-to-height repair for group 27792."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    side_match = re.search(r"\bAB\s*=\s*BC\s*=\s*AC\s*=\s*([^,;.]+)", formula)
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must declare AB=BC=AC and give the side")
    if not re.search(r"(?:высот[^.]*\bCH\b|\bCH\b[^.]*высот)", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request height CH")
    side_latex = side_match.group(1).strip()
    side = _parse_positive_value(side_latex)
    height = sp.simplify(side * sp.sqrt(3) / 2)
    answer = _answer_text(height)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> равносторонний, '
        'значит, все его углы равны <span data-inline-latex="60^{\\circ}"></span>. Получаем:</p>'
        '<center><p><span data-inline-latex="'
        + rf"CH=AC\sin \angle A={side_latex}\sin 60^{{\circ}}={side_latex}\cdot \frac{{\sqrt{{3}}}}{{2}}={_latex_number(height)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27793_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equilateral-height-to-side repair for group 27793."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if not re.search(r"равно.*сторон", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an equilateral triangle")
    if not re.search(r"высот[^.]*\bCH\b|\bCH\b[^.]*высот", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must give height CH")
    request = _request_text(condition_html)
    if not re.search(r"сторон", request, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the triangle sides")
    values = _inline_formulas(condition_html)
    if len(values) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly one height value")
    height_latex = values[0].strip()
    height = _parse_positive_value(height_latex)
    side = sp.simplify(2 * height / sp.sqrt(3))
    answer = _answer_text(side)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> равносторонний, '
        'значит, все его углы равны <span data-inline-latex="60^{\\circ}"></span>. Получаем:</p>'
        '<center><p><span data-inline-latex="'
        + rf"AC=\frac{{CH}}{{\sin \angle A}}=\frac{{{height_latex}}}{{\sin 60^{{\circ}}}}={height_latex}\cdot \frac{{2}}{{\sqrt{{3}}}}={_latex_number(side)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27794_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the base-and-altitude-to-vertex-angle repair for 27794."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    base_match = re.search(r"\bAB\s*=\s*(.+?)(?=\s+Найд|[,;.]|$)", formula)
    if base_match is None:
        raise IsoscelesTrianglePlanError("condition must give base AB")
    if not re.search(r"высот[^.]*\bCH\b|\bCH\b[^.]*высот", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must give altitude CH")
    if not re.search(r"угол\s+C\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle C")
    height_values = tuple(value.strip() for value in _inline_formulas(condition_html) if "=" not in value)
    if len(height_values) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly one altitude value")
    base_latex = base_match.group(1).strip()
    height_latex = height_values[0]
    base = _parse_positive_value(base_latex)
    height = _parse_positive_value(height_latex)
    half_base = sp.simplify(base / 2)
    side = sp.simplify(sp.sqrt(half_base**2 + height**2))
    if sp.simplify(side - base) != 0:
        raise IsoscelesTrianglePlanError("base and altitude do not produce an equilateral triangle")
    answer = "60"
    solution_html = (
        '<p>Высота равнобедренного треугольника является медианой, поэтому</p>'
        '<center><p><span data-inline-latex="'
        + rf"AH=\frac{{AB}}{{2}}={_latex_number(half_base)}"
        + '"></span>.</p></center>'
        '<p>В прямоугольном <span data-inline-latex="\\triangle AHC"></span> '
        'по теореме Пифагора</p><center><p><span data-inline-latex="'
        + rf"AC=\sqrt{{AH^{{2}}+CH^{{2}}}}=\sqrt{{({_latex_number(half_base)})^{{2}}+({height_latex})^{{2}}}}={_latex_number(side)}"
        + '"></span>.</p></center>'
        '<p>Получили <span data-inline-latex="AC=BC=AB"></span>, поэтому '
        'треугольник <span data-inline-latex="ABC"></span> равносторонний и '
        '<span data-inline-latex="\\angle C=60^{\\circ}"></span>.</p>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27795_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-vertex-angle-to-altitude repair for 27795."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    side_match = re.search(r"\bAC\s*=\s*BC\s*=\s*([^,;.]+)", formula)
    angle_match = re.search(
        r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if side_match is None or angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and angle C")
    if not re.search(r"высот[^.]*\bAH\b|\bAH\b[^.]*высот", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request altitude AH")
    side_latex = side_match.group(1).strip()
    side = _parse_positive_value(side_latex)
    angle = int(angle_match.group(1))
    if angle <= 0 or angle >= 180:
        raise IsoscelesTrianglePlanError("vertex angle must form a triangle")
    sine = sp.simplify(sp.sin(sp.pi * angle / 180))
    if sine.has(sp.sin):
        raise IsoscelesTrianglePlanError("vertex angle has no supported exact sine")
    height = sp.simplify(side * sine)
    answer = _answer_text(height)
    solution_html = (
        '<p>В прямоугольном <span data-inline-latex="\\triangle AHC"></span> '
        'высота <span data-inline-latex="AH"></span> является катетом, противолежащим углу '
        '<span data-inline-latex="C"></span>. Поэтому</p><center><p><span data-inline-latex="'
        + rf"AH=AC\sin \angle C={side_latex}\sin {angle}^{{\circ}}={side_latex}\cdot {_latex_number(sine)}={_latex_number(height)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27796_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-altitude-to-acute-angle repair for 27796."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if not re.search(r"остро.*уголь", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an acute triangle")
    side_match = re.search(r"\bAC\s*=\s*BC\s*=\s*([^,;.]+)", formula)
    height_match = re.search(r"высот[^.]*\bAH\b\s+равна\s*([^,;.]+)", formula, re.IGNORECASE)
    if side_match is None or height_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and altitude AH")
    if not re.search(r"угол\s+C\b|градус[^.]*угла\s+C\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle C")
    side_latex = side_match.group(1).strip()
    height_latex = height_match.group(1).strip()
    side = _parse_positive_value(side_latex)
    height = _parse_positive_value(height_latex)
    ratio = sp.simplify(height / side)
    if ratio >= 1:
        raise IsoscelesTrianglePlanError("altitude must be shorter than the equal side")
    angle = sp.simplify(180 * sp.asin(ratio) / sp.pi)
    if angle.has(sp.asin) or angle.is_rational is not True:
        raise IsoscelesTrianglePlanError("altitude ratio has no supported exact acute angle")
    answer = _answer_text(angle)
    solution_html = (
        '<p>В прямоугольном <span data-inline-latex="\\triangle AHC"></span> '
        '<span data-inline-latex="AC"></span> — гипотенуза. По определению синуса</p>'
        '<center><p><span data-inline-latex="'
        + rf"\sin \angle C=\frac{{AH}}{{AC}}=\frac{{{height_latex}}}{{{side_latex}}}={_latex_number(ratio)}"
        + '"></span>,</p></center><p>откуда, так как угол <span data-inline-latex="C"></span> острый,</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle C={_latex_number(angle)}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27797_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the altitude-and-vertex-angle-to-equal-side repair for 27797."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    height_match = re.search(r"высот[^.]*\bAH\b\s+равна\s*([^,;.]+)", formula, re.IGNORECASE)
    angle_match = re.search(
        r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if height_match is None or angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give altitude AH and angle C")
    request = _request_text(condition_html)
    if not re.search(r"\bAC\b", request) or re.search(r"\b(?:AB|BC|AH|BH|CH)\b", request):
        raise IsoscelesTrianglePlanError("condition must request AC")
    height_latex = height_match.group(1).strip()
    height = _parse_positive_value(height_latex)
    angle = int(angle_match.group(1))
    if angle <= 0 or angle >= 180:
        raise IsoscelesTrianglePlanError("vertex angle must form a triangle")
    sine = sp.simplify(sp.sin(sp.pi * angle / 180))
    if sine.has(sp.sin):
        raise IsoscelesTrianglePlanError("vertex angle has no supported exact sine")
    side = sp.simplify(height / sine)
    answer = _answer_text(side)
    reciprocal = sp.simplify(1 / sine)
    solution_html = (
        '<p>Найдём длину стороны <span data-inline-latex="AC"></span> из '
        'прямоугольного <span data-inline-latex="\\triangle ACH"></span>:</p>'
        '<center><p><span data-inline-latex="'
        + rf"AC=\frac{{AH}}{{\sin \angle C}}=\frac{{{height_latex}}}{{\sin {angle}^{{\circ}}}}={height_latex}\cdot {_latex_number(reciprocal)}={_latex_number(side)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27798_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse equal-side-and-vertex-angle-to-altitude repair."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    side_match = re.search(r"\bAC\s*=\s*BC\s*=\s*([^,;.]+)", formula)
    angle_match = re.search(
        r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if side_match is None or angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and angle C")
    if not re.search(r"высот[^.]*\bAH\b|\bAH\b[^.]*высот", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request altitude AH")
    side_latex = side_match.group(1).strip()
    side = _parse_positive_value(side_latex)
    angle = int(angle_match.group(1))
    if angle <= 90 or angle >= 180:
        raise IsoscelesTrianglePlanError("group 27798 requires an obtuse angle C")
    supplement = 180 - angle
    sine = sp.simplify(sp.sin(sp.pi * supplement / 180))
    if sine.has(sp.sin):
        raise IsoscelesTrianglePlanError("supplementary angle has no supported exact sine")
    height = sp.simplify(side * sine)
    answer = _answer_text(height)
    solution_html = (
        '<p>Так как основание высоты лежит на продолжении стороны '
        '<span data-inline-latex="BC"></span>,</p><center><p><span data-inline-latex="'
        + rf"\angle ACH=180^{{\circ}}-\angle C={supplement}^{{\circ}}"
        + '"></span>.</p></center><p>В прямоугольном '
        '<span data-inline-latex="\\triangle ACH"></span> получаем:</p>'
        '<center><p><span data-inline-latex="'
        + rf"AH=AC\sin \angle ACH={side_latex}\sin {supplement}^{{\circ}}={side_latex}\cdot {_latex_number(sine)}={_latex_number(height)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27799_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the base-and-included-angle-to-equal-side repair for 27799."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    angle_match = re.search(
        r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|\^\\circ|°)",
        formula,
        re.IGNORECASE,
    )
    base_match = re.search(r"\bAB\s*=\s*(.+?)(?=\s+Найд|[,;.]|$)", formula)
    if angle_match is None or base_match is None:
        raise IsoscelesTrianglePlanError("condition must give angle C and base AB")
    request = _request_text(condition_html)
    if not re.search(r"\bAC\b", request) or re.search(r"\b(?:AB|BC|AH|BH|CH)\b", request):
        raise IsoscelesTrianglePlanError("condition must request AC")
    angle = int(angle_match.group(1))
    if angle <= 0 or angle >= 180:
        raise IsoscelesTrianglePlanError("included angle must form a triangle")
    base_latex = base_match.group(1).strip()
    base = _parse_positive_value(base_latex)
    cosine = sp.simplify(sp.cos(sp.pi * angle / 180))
    if cosine.has(sp.cos):
        raise IsoscelesTrianglePlanError("included angle has no supported exact cosine")
    denominator = sp.simplify(2 * (1 - cosine))
    side = sp.simplify(base / sp.sqrt(denominator))
    answer = _answer_text(side)
    solution_html = (
        '<p>По теореме косинусов и с учётом '
        '<span data-inline-latex="AC=BC"></span>:</p><center><p><span data-inline-latex="'
        + r"AB^{2}=AC^{2}+BC^{2}-2AC\cdot BC\cos \angle C=2AC^{2}\left(1-\cos \angle C\right)"
        + '"></span>.</p></center><p>Следовательно,</p><center><p><span data-inline-latex="'
        + r"AC=\sqrt{\frac{AB^{2}}{2\left(1-\cos \angle C\right)}}"
        + rf"=\sqrt{{\frac{{({base_latex})^{{2}}}}{{{_latex_number(denominator)}}}}}={_latex_number(side)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27800_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-included-angle-to-base repair for 27800."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    angle_match = re.search(
        r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|\^\\circ|°)",
        formula,
        re.IGNORECASE,
    )
    side_match = re.search(
        r"\bAC\s*=\s*(?!\s*BC\b)(.+?)(?=\s+Найд|[,;.]|$)",
        formula,
    )
    if angle_match is None or side_match is None:
        raise IsoscelesTrianglePlanError("condition must give angle C and side AC")
    request = _request_text(condition_html)
    if not re.search(r"\bAB\b", request) or re.search(r"\b(?:AC|BC|AH|BH|CH)\b", request):
        raise IsoscelesTrianglePlanError("condition must request AB")
    angle = int(angle_match.group(1))
    if angle <= 0 or angle >= 180:
        raise IsoscelesTrianglePlanError("included angle must form a triangle")
    side_latex = side_match.group(1).strip()
    side = _parse_positive_value(side_latex)
    cosine = sp.simplify(sp.cos(sp.pi * angle / 180))
    if cosine.has(sp.cos):
        raise IsoscelesTrianglePlanError("included angle has no supported exact cosine")
    factor = sp.simplify(2 * (1 - cosine))
    base = sp.simplify(side * sp.sqrt(factor))
    side_squared = sp.simplify(side**2)
    base_squared = sp.simplify(base**2)
    cross_term = sp.simplify(-2 * side_squared * cosine)
    cross_operator = "+" if cross_term >= 0 else "-"
    cross_term_latex = _latex_number(abs(cross_term))
    answer = _answer_text(base)
    solution_html = (
        '<p>Найдём косинус данного угла:</p>'
        '<center><p><span data-inline-latex="'
        + rf"\cos \angle C=\cos {angle}^{{\circ}}={_latex_number(cosine)}"
        + '"></span>.</p></center>'
        '<p>По теореме косинусов:</p>'
        '<center><p><span data-inline-latex="'
        + r"AB^{2}=AC^{2}+BC^{2}-2AC\cdot BC\cos \angle C"
        + '"></span>.</p></center>'
        '<p>Так как <span data-inline-latex="AC=BC=' + side_latex
        + '"></span>, подставим известные значения и последовательно выполним вычисления:</p>'
        '<center><p><span data-inline-latex="'
        + rf"AB^{{2}}=({side_latex})^{{2}}+({side_latex})^{{2}}"
        + rf"-2\cdot({side_latex})\cdot({side_latex})\cdot({_latex_number(cosine)})"
        + rf"\iff AB^{{2}}={_latex_number(side_squared)}+{_latex_number(side_squared)}"
        + rf"-2\cdot {_latex_number(side_squared)}\cdot({_latex_number(cosine)})"
        + rf"\iff AB^{{2}}={_latex_number(side_squared)}+{_latex_number(side_squared)}"
        + rf"{cross_operator}{cross_term_latex}"
        + rf"\iff AB^{{2}}={_latex_number(base_squared)}"
        + '"></span>.</p></center>'
        '<p>Длина стороны положительна, поэтому</p>'
        '<center><p><span data-inline-latex="'
        + rf"AB=\sqrt{{{_latex_number(base_squared)}}}={_latex_number(base)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
        refresh_solution=True,
    )


def build_group_628232_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the equal-side-and-tangent to base repair for group 628232."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html).replace("А", "A").replace("В", "B").replace("С", "C")
    side_match = re.search(
        r"(?:AC\s*=\s*BC|BC\s*=\s*AC)\s*=\s*"
        r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and their length")
    tangent_latex = _inline_assignment(condition_html, r"\\tg\s*\\angle\s*A\s*=")
    request = _request_text(condition_html)
    if not re.search(r"\bAB\b", request) or re.search(r"\b(?:AC|BC|AH|BH|CH)\b", request):
        raise IsoscelesTrianglePlanError("condition must request AB")
    side_latex = side_match.group(1)
    side = _parse_positive_value(side_latex)
    tangent = _parse_positive_value(tangent_latex)
    half_base = sp.simplify(side / sp.sqrt(1 + tangent**2))
    base = sp.simplify(2 * half_base)
    answer = _answer_text(base)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(str(solution.get("html") or ""))
    transformations: list[dict[str, Any]] = []
    if solution_missing:
        solution_images = [
            item for item in parent_solution_assets if item.get("asset_key") == "image_2"
        ]
        if len(solution_images) != 1:
            raise IsoscelesTrianglePlanError(
                "group 628232 parent must provide one solution image_2"
            )
        transformations.append(_asset_transformation(parent_condition_asset_id))
        solution_asset = _solution_asset_transformation(
            solution_images[0], expected_asset_key="image_2"
        )
        image_html = str(solution_asset["value"]["html"])
        solution_html = (
            image_html
            + '<p>Проведём высоту <span data-inline-latex="CH"></span>. '
            'Так как треугольник <span data-inline-latex="ABC"></span> '
            'равнобедренный, <span data-inline-latex="AH=HB"></span>. Пусть '
            '<span data-inline-latex="AH=x"></span>. По определению тангенса</p>'
            '<center><p><span data-inline-latex="'
            + rf"\tg \angle A=\frac{{CH}}{{AH}}={tangent_latex}"
            + rf"\iff CH={tangent_latex}x"
            + '"></span>.</p></center>'
            '<p>По теореме Пифагора для <span data-inline-latex="\\triangle ACH"></span>:</p>'
            '<center><p><span data-inline-latex="'
            + rf"AC^{{2}}=AH^{{2}}+CH^{{2}}"
            + rf"\iff ({side_latex})^{{2}}=x^{{2}}+({tangent_latex}x)^{{2}}"
            + rf"\iff x={_latex_number(half_base)}"
            + '"></span>.</p></center>'
            '<p>Следовательно,</p><center><p><span data-inline-latex="'
            + rf"AB=2AH=2\cdot {_latex_number(half_base)}={_latex_number(base)}"
            + '"></span>.</p></center>'
        )
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                solution_html,
                asset_keys=("image_2",),
            )
        )
        transformations.append(solution_asset)
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_group_676342_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the external-base-angle repair for group 676342."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html)
    if "равно" not in formula.lower() or "бедрен" not in formula.lower():
        raise IsoscelesTrianglePlanError("condition must state an isosceles triangle")
    if re.search(r"основа\S*\s+[AА][BВ]\b", formula, re.IGNORECASE) is None:
        raise IsoscelesTrianglePlanError("condition must state base AB")
    if re.search(
        r"(?:вершин\S*\s+[BВ]\b|угол\s+[CС][BВ]D\b)",
        formula,
        re.IGNORECASE,
    ) is None:
        raise IsoscelesTrianglePlanError("external angle must be at vertex B")
    angle_match = re.search(
        r"внешн\S*\s+угол.*?равен\s*([0-9]+)\s*°",
        formula,
        re.IGNORECASE,
    )
    if angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give one external angle")
    request = _request_text(condition_html)
    if not re.search(r"угл\S*\s+[AА]\b", request, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle A")
    external_angle = int(angle_match.group(1))
    if external_angle <= 90 or external_angle >= 180:
        raise IsoscelesTrianglePlanError("external base angle must be between 90 and 180")
    base_angle = 180 - external_angle
    answer = str(base_angle)
    solution_html = (
        '<p>По свойству смежных углов</p><center><p><span data-inline-latex="'
        + rf"\angle CBA=180^{{\circ}}-\angle CBD=180^{{\circ}}-{external_angle}^{{\circ}}={base_angle}^{{\circ}}"
        + '"></span>.</p></center>'
        '<p>Треугольник <span data-inline-latex="ABC"></span> равнобедренный, '
        'поэтому углы при основании <span data-inline-latex="AB"></span> равны:</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle CAB=\angle CBA={base_angle}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_701874_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the apex-exterior-angle to base-angle repair for group 701874."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html)
    if "равно" not in formula.lower() or "бедрен" not in formula.lower():
        raise IsoscelesTrianglePlanError("condition must state an isosceles triangle")
    if re.search(r"основа\S*\s+[AА][BВ]\b", formula, re.IGNORECASE) is None:
        raise IsoscelesTrianglePlanError("condition must state base AB")
    if re.search(r"вершин\S*\s+[CС]\b", formula, re.IGNORECASE) is None:
        raise IsoscelesTrianglePlanError("external angle must be at vertex C")
    angle_match = re.search(
        r"внешн\S*\s+угол.*?равен\s*([0-9]+)\s*°",
        formula,
        re.IGNORECASE,
    )
    if angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give one external angle")
    request = _request_text(condition_html)
    if not re.search(r"угл\S*\s+[AА][BВ][CС]\b", request, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle ABC")
    external_angle = int(angle_match.group(1))
    if external_angle <= 0 or external_angle >= 180:
        raise IsoscelesTrianglePlanError("external apex angle must be between 0 and 180")
    base_angle = sp.Rational(external_angle, 2)
    answer = _answer_text(base_angle)
    solution_html = (
        '<p>Внешний угол равен сумме двух несмежных с ним углов:</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle ABC+\angle CAB={external_angle}^{{\circ}}"
        + '"></span>.</p></center>'
        '<p>Углы при основании равнобедренного треугольника равны, поэтому</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle ABC=\angle CAB\iff 2\angle ABC={external_angle}^{{\circ}}"
        + rf"\iff \angle ABC={_latex_number(base_angle)}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )
