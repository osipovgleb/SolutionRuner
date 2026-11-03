"""Exact cube quantities, scaling factors and positive edge-increase solutions."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from ..equations.power_arithmetic import ScalarParser
from ..probability.common import COUNT, UnsupportedCondition, count
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError
from . import cube_section_model

PATTERNS = {
    "surface_from_volume": r"Объем куба равен\s+(.+?)\s*\.\s*Найдите площадь его поверхности\s*\.",
    "edge_from_surface_increase": r"Если каждое ребро куба увеличить на\s+(.+?)\s*,\s*то его площадь поверхности увеличится на\s+(.+?)\s*\.\s*Найдите ребро куба\s*\.",
    "volume_factor": r"Во сколько раз увеличится объем куба, если (?:все )?его ребра увеличить в\s+(.+?)\s+раза?\s*\?",
    "volume_from_diagonal": r"Диагональ куба равна\s+(.+?)\s*\.\s*Найдите его объем\s*\.",
    "diagonal_from_volume": r"Объем куба равен\s+(.+?)\s*\.\s*Найдите его диагональ\s*\.",
    "edge_from_volume_increase": r"Если каждое ребро куба увеличить на\s+(.+?)\s*,\s*то его объем увеличится на\s+(.+?)\s*\.\s*Найдите ребро куба\s*\.",
    "surface_factor": r"Во сколько раз увеличится площадь поверхности куба, если его ребро увеличить в\s+(.+?)\s+раза?\s*\?",
    "surface_from_diagonal": r"Диагональ куба равна\s+(.+?)\s*\.\s*Найдите площадь его поверхности\s*\.",
    "volume_from_surface": r"Площадь поверхности куба равна\s+(.+?)\s*\.\s*Найдите его объем\s*\.",
    "surface_factor_from_volume_factor": r"Объем (?:первого|одного) куба в\s+(.+?)\s+раза? больше объема (?:второго|другого) куба\s*\.\s*Во сколько раз площадь поверхности (?:первого куба больше площади поверхности второго|второго куба меньше площади поверхности первого) куба\s*\?",
}
FACTOR_MODES = {"volume_factor", "surface_factor", "surface_factor_from_volume_factor"}
FORMULAS = {
    "surface_from_volume": lambda v: 6 * v[0] ** sp.Rational(2, 3),
    "edge_from_surface_increase": lambda v: (v[1] - 6 * v[0] ** 2) / (12 * v[0]),
    "volume_factor": lambda v: v[0] ** 3,
    "volume_from_diagonal": lambda v: (v[0] / sp.sqrt(3)) ** 3,
    "diagonal_from_volume": lambda v: (3 * sp.sqrt(3) * v[0]) ** sp.Rational(1, 3),
    "edge_from_volume_increase": lambda v: (
        (sp.sqrt((4 * v[1] - v[0] ** 3) / (3 * v[0])) - v[0]) / 2
    ),
    "surface_factor": lambda v: v[0] ** 2,
    "surface_from_diagonal": lambda v: 2 * v[0] ** 2,
    "volume_from_surface": lambda v: (v[0] / 6) ** sp.Rational(3, 2),
    "surface_factor_from_volume_factor": lambda v: v[0] ** sp.Rational(2, 3),
}


@dataclass(frozen=True)
class CubeQuantity:
    mode: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr


def _positive(raw, *, words=False):
    value = (
        sp.Integer(count(raw))
        if words and re.search(r"[а-я]", raw) and re.fullmatch(COUNT, raw)
        else ScalarParser(raw).parse()
    )
    if (
        value.is_real is not True
        or value.is_finite is not True
        or value.is_positive is not True
    ):
        raise ContentPlanError("cube values must be positive finite real numbers")
    return value


def read_question(html, source=None):
    if not isinstance(html, str):
        raise ContentPlanError("complete cube condition HTML is required")
    if re.search(r"<img\b", html, re.IGNORECASE) and (
        not isinstance(source, str) or not source
    ):
        raise ContentPlanError("a reviewed cube condition image identifier is required")
    try:
        text = _text(
            html,
            source,
            labels="ABCDKLMabcd",
            extra_identifiers=cube_section_model.IDENTIFIERS,
        ).replace("ё", "е")
        section = cube_section_model.read(text)
        if section is not None:
            return section
        for mode, pattern in PATTERNS.items():
            match = re.fullmatch(pattern, text)
            if match is None:
                continue
            given = tuple(
                _positive(v, words=mode in FACTOR_MODES) for v in match.groups()
            )
            if mode in FACTOR_MODES and given[0] <= 1:
                raise ContentPlanError("an increase factor must exceed one")
            if mode.endswith("_increase"):
                increment, delta = given
                boundary = (
                    6 * increment**2
                    if mode == "edge_from_surface_increase"
                    else increment**3
                )
                if delta <= boundary:
                    raise ContentPlanError("the original cube edge must be positive")
            answer = sp.simplify(FORMULAS[mode](given))
            if (
                answer.is_real is not True
                or answer.is_finite is not True
                or answer.is_positive is not True
            ):
                raise ContentPlanError("the cube quantity is not positive and finite")
            return CubeQuantity(mode, given, answer)
    except (UnsupportedCondition, AltitudeSolveError) as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError("one complete reviewed cube question is required")
