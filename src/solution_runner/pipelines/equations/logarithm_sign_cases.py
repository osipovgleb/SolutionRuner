"""Solve source-style base-sign cases through the existing exact interval engine."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exponential_inequality_common_base import read_terms
from .logarithm_rationalization import answer
from .rational_inequality import FLIPPED
from .rational_inequality_parser import X, polynomial
from .rational_substitution_preimages import comparison, excluded_points
from .variable_logarithm_parser import Atoms, VariableLogarithmParser


def side(base, increasing):
    return comparison(base - 1, ">" if increasing else "<").solution


def read_atoms(formula, *, product):
    formula = re.sub(r"\\log_x(?![a-zA-Z])", r"\\log_{x}", formula.removesuffix("."))
    atoms = Atoms()
    left, right, denominators, operator = read_terms(
        formula, reader=lambda text: VariableLogarithmParser(text, atoms=atoms)
    )
    if len(atoms.values) != 2 or operator != "<=":
        raise UnsupportedCondition(
            "two complete variable logarithms and a nonstrict comparison are required"
        )
    first, second = atoms.values
    expected = (
        (first.symbol * second.symbol, sp.S.Zero)
        if product
        else (first.symbol, second.symbol)
    )
    if (left.value, right.value) != expected:
        raise UnsupportedCondition(
            "the whole outer logarithm product or comparison must be recognized"
        )
    if product:
        if any(
            not value.is_polynomial(X) or polynomial(value).degree() != 1
            for atom in atoms.values
            for value in (atom.base, atom.argument)
        ):
            raise UnsupportedCondition(
                "the reviewed product has four complete affine bases and arguments"
            )
    else:
        if (
            first.argument != second.argument
            or first.argument.is_Rational is not True
            or not 1 < first.argument <= 1000
        ):
            raise UnsupportedCondition(
                "one common constant argument greater than one is required"
            )
        for atom in atoms.values:
            n, d = sp.fraction(sp.cancel(atom.base))
            if (
                not atom.base.has(X)
                or max(polynomial(n).degree(), polynomial(d).degree()) > 1
            ):
                raise UnsupportedCondition(
                    "complete affine rational variable bases are required"
                )
    poles = excluded_points((*denominators, *(atom.base - 1 for atom in atoms.values)))
    domain = sp.Intersection(
        *(
            comparison(value, ">").solution
            for atom in atoms.values
            for value in (atom.base, atom.argument)
        )
    ) - sp.FiniteSet(*poles)
    return tuple(atoms.values), poles, domain


@dataclass(frozen=True)
class SignRegion:
    increasing: bool
    argument_above: bool
    domain: object


def sign_regions(atom, domain, sign):
    result = []
    for increasing in (True, False):
        argument_above = increasing if sign > 0 else not increasing
        region = sp.Intersection(
            domain, side(atom.base, increasing), side(atom.argument, argument_above)
        )
        if region != sp.EmptySet:
            result.append(SignRegion(increasing, argument_above, region))
    if sp.Union(*(r.domain for r in result)) != domain:
        raise UnsupportedCondition(
            "the fixed logarithm sign must be proved on the entire original domain"
        )
    return tuple(result)


@dataclass(frozen=True)
class ProductCase:
    increasing: bool
    domain: object
    operator: str
    stage: object
    solution: object


@dataclass(frozen=True)
class ProductCases:
    atoms: tuple
    poles: tuple
    domain: object
    fixed_index: int
    fixed_sign: int
    sign_regions: tuple
    target: str
    cases: tuple
    solution: object

    @property
    def varying(self):
        return self.atoms[1 - self.fixed_index]

    @property
    def answer(self):
        return answer(self.solution)


def product_cases(formula):
    atoms, poles, domain = read_atoms(formula, product=True)
    fixed = None
    for index, atom in enumerate(atoms):
        for sign, op in ((1, ">"), (-1, "<")):
            if (
                domain.is_subset(
                    comparison((atom.base - 1) * (atom.argument - 1), op).solution
                )
                is True
            ):
                fixed = (index, sign)
                break
        if fixed is not None:
            break
    if fixed is None:
        raise UnsupportedCondition(
            "one factor must have a strict constant sign on the complete original domain"
        )
    index, sign = fixed
    varying = atoms[1 - index]
    target = "<=" if sign > 0 else ">="
    cases = []
    for increasing in (True, False):
        region = domain.intersect(side(varying.base, increasing))
        operator = target if increasing else FLIPPED[target]
        stage = comparison(varying.argument - 1, operator)
        cases.append(
            ProductCase(
                increasing, region, operator, stage, region.intersect(stage.solution)
            )
        )
    solution = sp.Union(*(case.solution for case in cases))
    return ProductCases(
        atoms,
        poles,
        domain,
        index,
        sign,
        sign_regions(atoms[index], domain, sign),
        target,
        tuple(cases),
        solution,
    )


@dataclass(frozen=True)
class OrderCase:
    left_increasing: bool
    right_increasing: bool
    domain: object
    stage: object
    solution: object


@dataclass(frozen=True)
class BaseOrder:
    atoms: tuple
    poles: tuple
    domain: object
    cases: tuple
    solution: object

    @property
    def argument(self):
        return self.atoms[0].argument

    @property
    def answer(self):
        return answer(self.solution)


def base_order(formula):
    atoms, poles, domain = read_atoms(formula, product=False)
    first, second = atoms
    cases = []
    for left, right in ((True, True), (False, True), (True, False), (False, False)):
        region = sp.Intersection(
            domain, side(first.base, left), side(second.base, right)
        )
        if region == sp.EmptySet:
            continue
        stage = comparison(first.base - second.base, ">=") if left == right else None
        solution = (
            region.intersect(stage.solution)
            if stage
            else region
            if not left
            else sp.EmptySet
        )
        cases.append(OrderCase(left, right, region, stage, solution))
    return BaseOrder(
        atoms, poles, domain, tuple(cases), sp.Union(*(c.solution for c in cases))
    )
