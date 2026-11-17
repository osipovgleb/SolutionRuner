"""Exact facts and reviewed identities for right-triangle altitude solving."""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp


class AltitudeSolveError(ValueError):
    """Report an ambiguous, inconsistent, or unsupported altitude condition."""


@dataclass(frozen=True)
class AltitudeSolution:
    """Hold one exact requested value and its dependency-ordered formula rows."""

    requested: str
    exact_value: sp.Expr
    answer: str
    rows: tuple[str, ...]
    givens: tuple[tuple[str, sp.Expr, str], ...] = ()
    values: tuple[tuple[str, sp.Expr], ...] = ()


@dataclass(frozen=True)
class _Derivation:
    """Describe the exact facts and display rows used to infer one quantity."""

    inputs: tuple[str, ...]
    rows: tuple[str, ...]


@dataclass(frozen=True)
class _Fact:
    """Store one positive exact value, display form, and optional derivation."""

    value: sp.Expr
    latex: str
    derivation: _Derivation | None


_LENGTHS = ("AB", "AC", "BC", "AH", "BH", "CH")
_TRIG = ("sinA", "cosA", "tgA", "sinB", "cosB", "tgB")
_QUANTITIES = set(_LENGTHS + _TRIG)
_RATIOS = (
    ("sinA", "BC", "AB"),
    ("sinA", "CH", "AC"),
    ("sinA", "BH", "BC"),
    ("cosA", "AC", "AB"),
    ("cosA", "AH", "AC"),
    ("cosA", "CH", "BC"),
    ("tgA", "BC", "AC"),
    ("tgA", "CH", "AH"),
    ("tgA", "BH", "CH"),
    ("sinB", "AC", "AB"),
    ("sinB", "AH", "AC"),
    ("sinB", "CH", "BC"),
    ("cosB", "BC", "AB"),
    ("cosB", "CH", "AC"),
    ("cosB", "BH", "BC"),
    ("tgB", "AC", "BC"),
    ("tgB", "AH", "CH"),
    ("tgB", "CH", "BH"),
)
_PYTHAGOREAN = (
    ("AB", "AC", "BC"),
    ("AC", "AH", "CH"),
    ("BC", "BH", "CH"),
)
_TANGENT_HYPOTENUSE = (
    ("AB", "BC", "AC"),
    ("AC", "CH", "AH"),
    ("BC", "BH", "CH"),
)
_RATIO_VARIABLES = {
    ("BC", "AB"): "x",
    ("AC", "AB"): "x",
    ("BC", "AC"): "x",
    ("CH", "AC"): "y",
    ("AH", "AC"): "y",
    ("CH", "AH"): "y",
    ("BH", "BC"): "z",
    ("CH", "BC"): "z",
    ("BH", "CH"): "z",
    ("AC", "BC"): "x",
    ("AH", "CH"): "y",
    ("CH", "BH"): "z",
}
