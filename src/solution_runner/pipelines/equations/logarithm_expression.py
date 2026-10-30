"""Prepare exact logarithm calculations without reading the saved answer."""

from fractions import Fraction

from ..core.numbers import format_answer
from ..probability.common import UnsupportedCondition, finish
from .calculation_input import read_calculation
from .logarithm_parser import LogarithmParser
from .logarithm_proof import render


def build_context_repair_plan(context, *, two_methods=None, product_proof=False):
    _, condition, answer, solution, expression, parameters = read_calculation(context)
    if (
        parameters.bindings
        or parameters.positive
        or parameters.nonzero
        or parameters.definition
    ):
        raise UnsupportedCondition(
            "numeric logarithms do not accept variable declarations"
        )
    node = LogarithmParser(expression).parse()
    if node.value.is_Rational is not True:
        raise UnsupportedCondition(
            "the logarithmic result is not an exact rational number"
        )
    value = Fraction(int(node.value.p), int(node.value.q))
    html = render(node, two_methods=two_methods, product_proof=product_proof)
    return finish(condition, answer, solution, format_answer(value), html)
