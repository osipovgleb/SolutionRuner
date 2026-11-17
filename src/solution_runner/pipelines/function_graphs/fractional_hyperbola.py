"""Linear-over-linear hyperbolas: source geometry, two methods and formula repair."""

from __future__ import annotations

import hashlib
import re
from fractions import Fraction

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..triangles.isosceles.planner import (
    _normalized_content,
    _section,
    _section_transformation,
)
from .fractional_hyperbola_geometry import ASSET_DIR as _ASSET_DIR
from .fractional_hyperbola_geometry import NS as _NS
from .fractional_hyperbola_geometry import annotate as _annotate
from .fractional_hyperbola_geometry import graph_evidence, registry
from .fractional_hyperbola_proof import alternative_proof, first_proof
from .hyperbola import RepairPlan, answer_text

annotate = _annotate
ASSET_DIR = _ASSET_DIR
NS = _NS


def entry(context):
    c = _normalized_content(context)
    condition = _section(c, "condition")
    assets = [
        a
        for a in c.get("assets", [])
        if a.get("asset_key") == "image_1"
        and "image_1" in (condition or {}).get("asset_keys", [])
    ]
    if len(assets) != 1:
        raise ContentPlanError("unique image_1 required")
    found = registry()["conditions"].get(assets[0].get("asset_id"))
    if found is None:
        unsupported = registry().get("unsupported_conditions", {})
        reason = unsupported.get(assets[0].get("asset_id"))
        raise ContentPlanError(
            reason or "fractional hyperbola source needs an audited registration"
        )
    return found


def required_assets(context):
    e = entry(context)
    return tuple(
        {
            "source_asset_id": e[m]["source_asset_id"],
            "section_id": "solution:1",
            "alt_text": alt,
        }
        for m, alt in [
            ("points", "Три точки гиперболы"),
            ("offset", "Отступ от асимптоты гиперболы"),
        ]
    )


def _verify_points(facts, coefficients):
    k, a, b = coefficients
    # Solve the three-point linear system independently of the asymptotes.
    matrix = [
        [px, Fraction(1), -py, px * py]
        for px, py in (facts["point"], facts["second"], facts["third"])
    ]
    for col in range(3):
        pivot = next((i for i in range(col, 3) if matrix[i][col]), None)
        if pivot is None:
            raise ContentPlanError("three-point system is singular")
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        divisor = matrix[col][col]
        matrix[col] = [v / divisor for v in matrix[col]]
        for i in range(3):
            if i != col:
                factor = matrix[i][col]
                matrix[i] = [v - factor * w for v, w in zip(matrix[i], matrix[col])]
    if tuple(r[-1] for r in matrix) != (k, a, b):
        raise ContentPlanError("three-point system disagrees with graph")


def _prepare_changes(context, sections, html, keys, result):
    condition, solution, answer = sections
    old_html = str(solution.get("html") or "") if solution else ""
    retired = set(registry().get("retired_asset_ids", []))
    retired_keys = tuple(
        a["asset_key"]
        for a in _normalized_content(context)["assets"]
        if a.get("asset_id") in retired
    )
    # Keep unrelated editorial illustrations.
    for img in re.findall(r"<img\b[^>]*>", old_html, re.IGNORECASE):
        if not any(key in img for key in (*keys, "image_1", *retired_keys)):
            html += img
    changes = []
    cleaned = (
        condition["html"]
        .replace("\u00ad", "")
        .replace(r"f(x)=\frac{k}{x}+ax+b", r"f(x)=\frac{kx+a}{x+b}")
    )
    if cleaned != condition["html"]:
        changes.append(
            _section_transformation(
                condition,
                "condition",
                "Условие",
                cleaned,
                asset_keys=tuple(condition.get("asset_keys", [])),
            )
        )
    solution_keys = (
        tuple(
            dict.fromkeys(
                tuple(
                    key
                    for key in solution.get("asset_keys", [])
                    if key not in retired_keys
                )
                + tuple(keys)
            )
        )
        if solution
        else tuple(keys)
    )
    comparable = lambda v: re.sub(r'\s+data-transformation-target-id="[^"]*"', "", v)
    if (
        not solution
        or comparable(old_html) != comparable(html)
        or tuple(solution.get("asset_keys", [])) != solution_keys
    ):
        changes.append(
            _section_transformation(
                solution, "solution", "Решение", html, asset_keys=solution_keys
            )
        )
    value = answer_text(result).replace(".", ",")
    old_answer = BeautifulSoup(
        str(answer.get("html") or "") if answer else "", "html.parser"
    ).get_text("", strip=True)
    if old_answer != value:
        changes.append(
            _section_transformation(
                answer,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{value}</span></p>',
            )
        )
    return RepairPlan(value, tuple(changes))


def build_context_repair_plan(
    context, *, condition_asset_bytes, current_asset_content_type
):
    c = _normalized_content(context)
    condition = _section(c, "condition")
    solution = _section(c, "solution")
    answer = _section(c, "answer")
    if not condition or condition_asset_bytes is None:
        raise ContentPlanError("condition and graph required")
    if str(current_asset_content_type).split(";")[0].lower() != "image/svg+xml":
        raise ContentPlanError("fractional hyperbola graph must be SVG")
    e = entry(context)
    if hashlib.sha256(condition_asset_bytes).hexdigest() != e["sha256"]:
        raise ContentPlanError("source SVG differs from audited registration")
    facts = graph_evidence(condition_asset_bytes)
    k, a, b = (facts[key] for key in ("k", "a", "b"))
    _verify_points(facts, (k, a, b))
    from .hyperbola_questions import fractional

    abc_model, sought, whole = fractional(context)
    if whole and any(v.denominator != 1 for v in (k, a, b)):
        raise ContentPlanError("declared integer coefficients disagree with the graph")
    result = {"k": k, "a": a, "b": b}[sought]
    images = []
    keys = []
    for req in required_assets(context):
        asset = next(
            (
                a
                for a in _normalized_content(context)["assets"]
                if a.get("asset_id") == req["source_asset_id"]
            ),
            None,
        )
        if asset is None:
            raise ContentPlanError("required graph annotation is not attached")
        key = asset["asset_key"]
        aid = asset["asset_id"]
        keys.append(key)
        images.append(
            f'<center><img alt="{req["alt_text"]}" data-asset-id="{aid}" data-asset-key="{key}" src="/assets/{aid}"/></center>'
        )

    first = first_proof(facts, sought, result, images[0])
    alternative = alternative_proof(facts, sought, result, images[1])
    html = f'<section data-content-kind="solution" data-solution-title="Решение">{first}</section><section data-content-kind="solution" data-solution-title="Альтернативное решение">{alternative}</section>'
    if abc_model:
        # Consume row breaks before commands so \\k is a row break plus variable.
        # Rename only LaTeX variables; commands such as \frac and \begin stay intact.
        symbols = {"k": "a", "a": "b", "b": "c"}

        def renamed_formula(match):
            return (
                'data-inline-latex="'
                + re.sub(
                    r"\\\\|\\(?:begin|end)\{[^}]+\}|\\[A-Za-z]+|[A-Za-z]",
                    lambda token: symbols.get(token[0], token[0]),
                    match[1],
                )
                + '"'
            )

        html = re.sub(r'data-inline-latex="([^"]*)"', renamed_formula, html)
    return _prepare_changes(context, (condition, solution, answer), html, keys, result)
