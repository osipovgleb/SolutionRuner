"""Exact evaluation over every admissible sign branch of a given value."""

from dataclasses import dataclass
from fractions import Fraction

import sympy as sp

from ..core.numbers import format_answer
from ..probability.common import UnsupportedCondition, finish
from .power_arithmetic import ScalarParser
from .trig_angles import C, S, reduce_polynomial
from .trig_given_domain import Question, candidates, interval, read_question
from .trig_given_proof import render
from .trig_symbolic_parser import (
    SymbolicAtom,
    SymbolicTrigonometricParser,
    compile_atoms,
)


@dataclass
class Calculation:
    question: Question
    parser: SymbolicTrigonometricParser
    original: sp.Expr
    values: dict
    denominators: list
    theta: str
    variable: str
    reduced: sp.Expr
    answer: sp.Rational
    given: SymbolicAtom | None = None
    given_value: sp.Expr | None = None
    pairs: list | None = None


def calculate(context):
    question = read_question(context)
    parser = SymbolicTrigonometricParser(question.expression)
    original = parser.parse().value
    given = None
    given_value = None
    if question.relation:
        if question.relation.count("=") != 1:
            raise UnsupportedCondition("one given trigonometric equality is required")
        left, right = question.relation.split("=")
        before = set(parser.atoms)
        node = parser._nested(left)
        new = set(parser.atoms) - before
        if len(new) != 1 or node.value not in new:
            raise UnsupportedCondition(
                "the given equality must specify one sine, cosine or tangent"
            )
        given = parser.atoms[node.value]
        if given.shift != 0 or given.coefficient <= 0:
            raise UnsupportedCondition(
                "the given angle must be a positive unshifted multiple"
            )
        given_value = ScalarParser(right).parse()
    base, variable, values, denominators = compile_atoms(parser)
    if given and given.coefficient != base:
        raise UnsupportedCondition("the given angle must be the common argument")
    if question.domain and base != 1:
        raise UnsupportedCondition(
            "this angular interval is stated for the original single angle"
        )
    theta = (str(base) if base != 1 else "") + variable
    raw = original.xreplace(values)
    reduced = reduce_polynomial(raw)
    pairs = None
    if given:
        domain = interval(question.domain, variable)
        possible = candidates(given.function, given_value, domain)
        pairs = []
        answers = []
        for pair in possible:
            assignment = {S: pair[0], C: pair[1]}
            checked = [sp.simplify(d.subs(assignment)) for d in denominators]
            if any(d.is_zero is True for d in checked):
                continue
            if any(d.is_zero is not False for d in checked):
                raise UnsupportedCondition(
                    "an original denominator is not proved nonzero"
                )
            value = sp.simplify(reduced.subs(assignment))
            if value.is_Rational is not True:
                raise UnsupportedCondition(
                    "the given expression has no exact rational value"
                )
            pairs.append(pair)
            answers.append(value)
        if not answers or any(a != answers[0] for a in answers):
            raise UnsupportedCondition(
                "the condition is inconsistent or leaves the requested sign undetermined"
            )
        answer = answers[0]
    else:
        if question.domain or reduced.is_Rational is not True:
            raise UnsupportedCondition(
                "the symbolic expression is not constant on its original domain"
            )
        answer = reduced
    return Calculation(
        question,
        parser,
        original,
        values,
        denominators,
        theta,
        variable,
        reduced,
        answer,
        given,
        given_value,
        pairs,
    )


def build_context_repair_plan(
    context, *, via_cotangent=False, direct_tangent=False, two_methods=False
):
    calculation = calculate(context)
    q = calculation.question
    html = render(
        calculation,
        via_cotangent=via_cotangent,
        direct_tangent=direct_tangent,
        two_methods=two_methods,
    )
    answer = calculation.answer
    return finish(
        q.condition,
        q.answer,
        q.solution,
        format_answer(Fraction(int(answer.p), int(answer.q))),
        html,
    )
