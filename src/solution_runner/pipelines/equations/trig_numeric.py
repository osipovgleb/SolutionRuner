"""Prepare numeric trigonometric identities with original-domain verification."""

from fractions import Fraction
from typing import NamedTuple

import sympy as sp

from ..core.numbers import format_answer
from ..probability.common import UnsupportedCondition, finish, line
from .calculation_input import read_calculation
from .trig_angles import (
    C,
    S,
    angle_text,
    choose_base,
    latex,
    polynomial,
    reduce_polynomial,
)
from .trig_parser import TrigonometricParser
from .trig_table_proof import render as table_proof


class Calculation(NamedTuple):
    parser: TrigonometricParser
    base: sp.Rational
    substitutions: dict
    original: sp.Expr
    reduced: sp.Expr
    exact: sp.Rational


def calculate(expression):
    parser = TrigonometricParser(expression)
    node = parser.parse()
    if not parser.atoms:
        raise UnsupportedCondition("a trigonometric expression is required")
    atoms = list(parser.atoms.values())
    base = choose_base(atoms)
    substitutions = {
        symbol: polynomial(atom, base) for symbol, atom in parser.atoms.items()
    }
    for denominator in parser.denominators:
        value = reduce_polynomial(denominator.xreplace(substitutions))
        if value == 0:
            raise UnsupportedCondition("the original denominator is zero")
        if denominator.is_zero is not False:
            actual = denominator.xreplace(
                {s: a.actual() for s, a in parser.atoms.items()}
            )
            if actual.is_zero is not False:
                raise UnsupportedCondition(
                    "the original trigonometric denominator is not proved nonzero"
                )
    raw = node.value.xreplace(substitutions)
    reduced = reduce_polynomial(raw)
    exact = reduced
    if exact.free_symbols:
        if base.q not in [1, 2, 3, 4, 6, 8, 12]:
            raise UnsupportedCondition(
                "the trigonometric identity does not reduce to an exact rational"
            )
        exact = sp.simplify(
            exact.subs({S: sp.sin(base * sp.pi), C: sp.cos(base * sp.pi)})
        )
    if exact.is_Rational is not True:
        raise UnsupportedCondition(
            "the trigonometric result is not an exact rational number"
        )
    return Calculation(parser, base, substitutions, node.value, reduced, exact)


def _double_form(expression, base, degrees):
    expanded = sp.expand(expression)
    for shape, coefficient, function in [
        (S * C, sp.expand(expanded).coeff(S * C), "sin"),
        (1 - 2 * S * S, expanded.subs(S, 0).subs(C, 0), "cos"),
    ]:
        if not coefficient or coefficient.free_symbols:
            continue
        if sp.expand(expanded - coefficient * shape) == 0:
            factor = coefficient / 2 if function == "sin" else coefficient
            text = (
                rf"({sp.latex(factor)})\{function}("
                + angle_text(2 * base, degrees)
                + ")"
            )
            exact = factor * {"sin": sp.sin, "cos": sp.cos}[function](2 * base * sp.pi)
            return text, sp.simplify(exact)
    return None


def proof(expression, calculation):
    parser, base, substitutions, original, reduced, exact = calculation
    if all(a.q.q in [1, 2, 3, 4, 6] for a in parser.atoms.values()):
        return table_proof(expression, calculation)
    degrees = next(iter(parser.atoms.values())).degrees
    html = "<p>Используем периодичность, чётность и формулы приведения. При сокращении сохраняем ненулевые знаменатели исходного выражения.</p>"
    html += line(
        r"\sin(t+2\pi)=\sin t,\quad \cos(t+2\pi)=\cos t,\quad \tg(t+\pi)=\tg t"
    )
    html += line(
        r"\sin^2t+\cos^2t=1,\quad \sin2t=2\sin t\cos t,\quad \cos2t=1-2\sin^2t"
    )
    html += line(r"\sin(\frac\pi2-t)=\cos t,\quad \cos(\pi-t)=-\cos t")
    html += "<p>Приведём углы к общему аргументу:</p>"
    shown = set()
    for symbol, atom in parser.atoms.items():
        if atom.q == base and (
            atom.function == "sin"
            and substitutions[symbol] == S
            or atom.function == "cos"
            and substitutions[symbol] == C
        ):
            continue
        step = atom.text + "=" + latex(substitutions[symbol], base, degrees)
        if step not in shown:
            html += line(step)
            shown.add(step)
    html += "<p>Подставим полученные выражения и сократим либо приведём подобные слагаемые:</p>"
    substituted = sp.latex(
        original,
        symbol_names={
            symbol: "(" + latex(value, base, degrees) + ")"
            for symbol, value in substitutions.items()
        },
    )
    html += line(expression + "=" + substituted)
    html += line(substituted + "=" + latex(reduced, base, degrees))
    double = _double_form(reduced, base, degrees)
    if double:
        text, value = double
        if sp.simplify(value - exact) != 0:
            raise UnsupportedCondition(
                "the double-angle proof disagrees with the exact value"
            )
        html += "<p>Применим формулу двойного угла и табличное значение:</p>"
        html += line(latex(reduced, base, degrees) + "=" + text)
        html += line(text + "=" + sp.latex(exact))
    elif reduced.free_symbols:
        html += "<p>Вычислим оставшиеся табличные значения:</p>"
        if S in reduced.free_symbols:
            html += line(
                r"\sin("
                + angle_text(base, degrees)
                + ")="
                + sp.latex(sp.sin(base * sp.pi))
            )
        if C in reduced.free_symbols:
            html += line(
                r"\cos("
                + angle_text(base, degrees)
                + ")="
                + sp.latex(sp.cos(base * sp.pi))
            )
        html += line(latex(reduced, base, degrees) + "=" + sp.latex(exact))
    elif latex(reduced, base, degrees) != sp.latex(exact):
        html += line(latex(reduced, base, degrees) + "=" + sp.latex(exact))
    return html


def build_context_repair_plan(context):
    _, condition, answer, solution, expression, parameters = read_calculation(context)
    if (
        parameters.bindings
        or parameters.positive
        or parameters.nonzero
        or parameters.definition
    ):
        raise UnsupportedCondition(
            "numeric trigonometry accepts no variable constraints"
        )
    calculation = calculate(expression)
    html = proof(expression, calculation)
    exact = calculation.exact
    return finish(
        condition,
        answer,
        solution,
        format_answer(Fraction(int(exact.p), int(exact.q))),
        html,
    )
