"""Factor logarithm products and retain every original variable-base restriction."""

from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X, select_roots
from .exam_logarithmic_algebra import roots
from .exam_logarithmic_input import SYMBOLS, Atom, read_equation
from .exam_rational import Selection
from .exam_scalar import compare
from .logarithm_arithmetic import log_ratio, power


@dataclass(frozen=True)
class Branch:
    kind: str
    equation: sp.Expr
    candidates: tuple
    source: tuple = ()


@dataclass(frozen=True)
class Analysis:
    selection: Selection
    atoms: tuple
    canonical: tuple
    converted: sp.Expr
    factored: sp.Expr
    constraints: tuple
    branches: tuple
    positive: tuple
    method: str
    generic: bool = False


def constraints(atoms):
    result = []
    for a in atoms:
        result.extend(
            ((a.base, "positive"), (a.base - 1, "nonzero"), (a.argument, "positive"))
        )
        if a.denominator:
            result.append((a.argument - 1, "nonzero"))
    return tuple(dict.fromkeys((sp.expand(p), relation) for p, relation in result))


def allowed(value, conditions):
    return all(
        (
            compare(sp.simplify(p.subs(X, value)), sp.Integer(0)) > 0
            if relation == "positive"
            else compare(sp.simplify(p.subs(X, value)), sp.Integer(0)) != 0
        )
        for p, relation in conditions
    )


def canonicalize(atoms, expression):
    reference = atoms[0].base
    canonical = []
    mapping = {}
    for a in atoms:
        ratio = log_ratio(a.base, reference)
        base, multiplier = (
            (reference, ratio) if ratio.is_Rational else (a.base, sp.Integer(1))
        )
        key = (base, a.argument, a.root)
        found = next(
            (c for c in canonical if (c.base, c.argument, c.root) == key), None
        )
        if found is None:
            found = Atom(base, a.argument, a.root, SYMBOLS[len(canonical)])
            canonical.append(found)
        mapping[a.symbol] = multiplier * found.symbol
    expression = sp.expand(expression.subs(mapping, simultaneous=True))
    if len(canonical) == 3 and len({a.base for a in canonical}) == 1:
        for i in range(3):
            j, k = [n for n in range(3) if n != i]
            ratio = sp.cancel(
                canonical[i].argument / (canonical[j].argument * canonical[k].argument)
            )
            if ratio.is_Rational and ratio > 0:
                shift = log_ratio(reference, ratio)
                if shift.is_Rational:
                    expression = sp.expand(
                        expression.subs(
                            canonical[i].symbol,
                            canonical[j].symbol + canonical[k].symbol + shift,
                        )
                    )
                    break
    return tuple(canonical), expression


def logarithm_factor(factor, canonical):
    active = [a for a in canonical if factor.has(a.symbol)]
    if factor.has(X) or any(a.root for a in active):
        raise UnsupportedCondition(
            "a logarithm factor must have constant coefficients and polynomial arguments"
        )
    if len(active) == 1:
        atom = active[0]
        p = sp.Poly(factor, atom.symbol)
        if (
            p.degree() == 2
            and p.nth(2) > 0
            and sp.simplify(p.nth(1) ** 2 - 4 * p.nth(2) * p.nth(0)) < 0
        ):
            return None
        if p.degree() != 1:
            raise UnsupportedCondition("a vanishing logarithm factor must be linear")
        level = -p.nth(0) / p.nth(1)
        if level.is_Rational is not True:
            raise UnsupportedCondition("a rational logarithm level is required")
        target = power(atom.base, level)
        equation = sp.expand(atom.argument - target)
        return Branch("level", equation, roots(equation), (atom, level, target))
    if len(active) == 2:
        a, b = active
        u, v = factor.coeff(a.symbol), factor.coeff(b.symbol)
        if (
            a.base != b.base
            or u == 0
            or u != -v
            or sp.expand(factor - u * a.symbol - v * b.symbol) != 0
        ):
            raise UnsupportedCondition(
                "two logarithms must have the same base and opposite coefficients"
            )
        equation = sp.expand(a.argument - b.argument)
        return Branch("equal-arguments", equation, roots(equation), (a, b))
    raise UnsupportedCondition("one or two logarithms are required in each factor")


def factored(atoms, expression):
    canonical, converted = canonicalize(atoms, expression)
    if converted == 0:
        raise UnsupportedCondition("an identity would need an infinite solution set")
    _, factors = sp.factor_list(converted, *SYMBOLS, X)
    branches = []
    positive = []
    for factor, _ in factors:
        if factor.free_symbols & set(SYMBOLS):
            branch = logarithm_factor(factor, canonical)
            if branch is None:
                positive.append(factor)
            else:
                branches.append(branch)
        else:
            branches.append(Branch("polynomial", factor, roots(factor)))
    return canonical, converted, sp.factor(converted), tuple(branches), tuple(positive)


def variable(atoms, expression, parent):
    if len(atoms) != 2 or any(a.root for a in atoms):
        raise UnsupportedCondition(
            "two unrooted logarithms are required for variable bases"
        )
    a, b = atoms
    if (
        sp.cancel(expression - (a.symbol - 1 / b.symbol)) == 0
        and b.denominator
        and sp.expand(a.base - b.argument) == 0
        and "при этих условиях" in parent
    ):
        equation = sp.expand(a.argument - b.base)
        return "reciprocal", (Branch("reciprocal", equation, roots(equation), (a, b)),)
    if (
        sp.expand(expression - a.symbol + b.symbol) == 0
        and sp.expand(a.argument - b.argument) == 0
        and "на одз" in parent
    ):
        equations = (a.argument - 1, a.base - b.base)
        return "same-argument", tuple(
            Branch(kind, sp.expand(p), roots(p), (a, b))
            for kind, p in zip(("argument-one", "equal-bases"), equations)
        )
    raise UnsupportedCondition(
        "the complete variable-base identity must match the reviewed method"
    )


def analyze(formula, interval, bounds, parent_html):
    atoms, expression = read_equation(formula, extended=True)
    parent = (
        BeautifulSoup(parent_html, "html.parser")
        .get_text(" ", strip=True)
        .replace("\xad", "")
        .lower()
    )
    if not parent or any(s in parent for s in ("другое решение", "еще одно решение")):
        raise UnsupportedCondition("one complete reviewed logarithm method is required")
    conditions = constraints(atoms)
    if any(a.base.has(X) for a in atoms):
        method, branches = variable(atoms, expression, parent)
        canonical, converted, factorization, positive = (
            atoms,
            expression,
            expression,
            (),
        )
    else:
        if not any(
            s in parent
            for s in (
                "преобразуем уравнение",
                "запишем исходное уравнение",
                "уравнение имеет вид",
                "решим отдельно уравнение",
            )
        ):
            raise UnsupportedCondition(
                "the parent must factor the equation or equate logarithm arguments"
            )
        canonical, converted, factorization, branches, positive = factored(
            atoms, expression
        )
        method = "equality-note" if "примечание" in parent else "factor"
    proposed = [r for b in branches for r in b.candidates]
    accepted = [r for r in proposed if allowed(r, conditions)]
    all_roots, selected = select_roots(accepted, bounds)
    return Analysis(
        Selection(all_roots, selected, interval, bounds),
        atoms,
        canonical,
        converted,
        factorization,
        conditions,
        branches,
        positive,
        method,
        "уравнение имеет вид" in parent,
    )


def build_context_repair_plan(context, *, parent_solution_html=""):
    from .exam_input import repair
    from .exam_logarithmic_branch_proof import render
    from .exam_logarithmic_reference import read

    parts, formula, interval, bounds = read(context)
    a = analyze(formula, interval, bounds, parent_solution_html)
    if bool(context["normalized_content"].get("assets")) != (
        a.method == "equality-note"
    ):
        raise UnsupportedCondition(
            "the reviewed equality note and its reference icons must remain identifiable"
        )
    return repair(parts, *render(a))
