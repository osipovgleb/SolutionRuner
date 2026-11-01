"""Normalize certified reciprocal bases and positive argument powers into one log."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .exam_trigonometric_log_parser import Parser
from .logarithm_arithmetic import actual, log_ratio, power, prime_log
from .logarithm_parser import Node
from .power_arithmetic import ScalarParser


def numeric_bases(text):
    return re.sub(r"\\log_([2-9])(?=\s+\d)", lambda m: r"\log_{" + m[1] + "}", text)


def quadratic(formula):
    text = formula.replace(r"\left", "").replace(r"\right", "")
    return bool(
        re.search(r"\\log_(?:\{[^{}]+\}|[2-9])\s*\^\s*\{?2", text)
        or re.search(r"\(\s*\\log_[^=]*\)\s*\^\s*\{?2", text)
    )


class PolynomialParser(Parser):
    max_logs = 4

    def __init__(self, text, atoms, denominators, logs, depth=0, *, constants=None):
        super().__init__(numeric_bases(text), atoms, denominators, logs, depth)
        self.constants = [] if constants is None else constants

    def _nested(self, text):
        return PolynomialParser(
            text,
            self.atoms,
            self.denominators,
            self.logs,
            self.depth + 1,
            constants=self.constants,
        ).parse()

    def _make_log(self, base, argument, exponent, text):
        if argument.free_symbols:
            return super()._make_log(base, argument, exponent, text)
        if (
            base.is_Rational is not True
            or argument.is_Rational is not True
            or not sp.Rational(1, 1000) <= base <= 1000
            or not sp.Rational(1, 1000) <= argument <= 1000
            or len(self.constants) >= 2
        ):
            raise UnsupportedCondition(
                "bounded positive rational constant logs are required"
            )
        value = actual(log_ratio(base, argument))
        self.constants.append((base, argument, value))
        return Node(value**exponent, text, "constant_log")


@dataclass(frozen=True)
class CommonLogs:
    original_arguments: tuple
    relations: tuple
    constants: tuple
    cancelled: tuple = ()


def scalar_level(text):
    try:
        return ScalarParser(text).parse()
    except UnsupportedCondition:
        atoms, logs, constants = {}, [], []
        node = PolynomialParser(text, atoms, [], logs, constants=constants).parse()
        if atoms or logs or not constants:
            raise UnsupportedCondition("a constant log level is required")
        return node.value


def exact_power(base, level):
    logs = level.atoms(sp.log)
    if len(logs) > 4 or any(
        n.args[0].is_Integer is not True or n.args[0] <= 1 or not sp.isprime(n.args[0])
        for n in logs
    ):
        raise UnsupportedCondition(
            "the log level must reduce through positive prime logarithms"
        )
    converted = level.xreplace({n: prime_log(int(n.args[0])) for n in logs})
    result = power(base, converted)
    if result.free_symbols or result.is_positive is not True:
        raise UnsupportedCondition(
            "the log level must have an exact positive constant power"
        )
    return result


def declared_base(parent, bases):
    for node in BeautifulSoup(parent, "html.parser").select("[data-inline-latex]"):
        text = numeric_bases(node["data-inline-latex"])
        for m in re.finditer(r"\\log_", text):
            logs = []
            try:
                parser = Parser(text[m.start() :].replace("x", r"\alpha"), {}, [], logs)
                parser._primary()
            except UnsupportedCondition:
                continue
            if len(logs) == 1 and logs[0][1] in bases:
                return logs[0][1]
    raise UnsupportedCondition("the parent must show the chosen common logarithm base")


def normalize(value, logs, arguments, constants, parent):
    from .exam_trigonometric_log_polynomial import L

    bases = {e[1] for e in logs}
    same = len(set(arguments)) == len(bases) == 1
    if same and not constants:
        return (
            logs[0][1],
            arguments[0],
            sp.cancel(value.subs(dict.fromkeys((e[0] for e in logs), L))),
            None,
        )
    for argument in dict.fromkeys(arguments):
        powers = []
        for other in arguments:
            exponent = next(
                (n for n in (1, 2) if sp.expand(other - argument**n) == 0), None
            )
            if exponent is None:
                break
            powers.append(exponent)
        if len(powers) == len(arguments):
            break
    else:
        return None
    from .exam_trigonometric_compile import C, S

    if value.has(S, C):
        return None
    base = declared_base(parent, bases)
    factors = tuple(
        sp.simplify(n * actual(log_ratio(e[1], base)))
        for n, e in zip(powers, logs, strict=True)
    )
    if any(
        f.is_Rational is not True or not 0 < abs(f) <= 12 or f.q > 12 for f in factors
    ):
        raise UnsupportedCondition(
            "bounded rational common-log multipliers are required"
        )
    replacements = {e[0]: f * L for e, f in zip(logs, factors, strict=True)}
    polynomial = sp.cancel(value.subs(replacements))
    if polynomial.free_symbols - {L}:
        return None
    relations = tuple(
        dict.fromkeys(
            (e[1], arg, f)
            for e, arg, f in zip(logs, arguments, factors, strict=True)
            if e[1] != base or arg != argument
        )
    )
    data = CommonLogs(
        tuple(dict.fromkeys(arguments)), relations, tuple(dict.fromkeys(constants))
    )
    return base, argument, polynomial, data


def bounded_level(base, level):
    if level.is_Rational is True:
        return abs(level) <= 20 and level.q <= 12
    target = exact_power(base, level)
    return (
        compare(level, -sp.Integer(20)) >= 0
        and compare(level, sp.Integer(20)) <= 0
        and target.is_Rational is True
        and sp.Rational(1, 1000) <= target <= 1000
    )


def argument_text(nodes, logs, arguments, argument):
    wanted = {e[0] for e, arg in zip(logs, arguments, strict=True) if arg == argument}

    def find(node):
        if node.kind == "log" and node.value.free_symbols <= wanted:
            return node.text
        return next((v for n in node.children if (v := find(n))), "")

    return next(v for n in nodes if (v := find(n)))


def cancellation(nodes, atoms, denominators, logs, arguments, value):
    from .exam_trigonometric_compile import C, S
    from .exam_trigonometric_radical_equation import compile_values

    if nodes[1].value != 0:
        return ()
    numerator, denominator = sp.fraction(nodes[0].value)
    if not denominator.free_symbols:
        return ()
    (numerator, denominator), _, _ = compile_values(
        [numerator, denominator],
        atoms,
        denominators,
        extra_symbols=tuple(e[0] for e in logs),
    )
    if (
        denominator.free_symbols - {S, C}
        or not denominator.free_symbols
        or value.has(S, C)
        or sp.cancel(numerator - denominator * value) != 0
    ):
        return ()
    return (
        denominator,
        value,
        tuple((e[0], e[1], arg) for e, arg in zip(logs, arguments, strict=True)),
    )


def parse_expression(formula):
    from .exam_trigonometric_radical_equation import compile_values
    from .power_arithmetic import clean

    text = clean(numeric_bases(formula)).removesuffix(".")
    if text.count("=") != 1:
        raise UnsupportedCondition("one complete log-polynomial equality is required")
    atoms, denominators, logs, constants = {}, [], [], []
    nodes = [
        PolynomialParser(
            part.replace("x", r"\alpha"), atoms, denominators, logs, constants=constants
        ).parse()
        for part in text.split("=")
    ]
    value = nodes[0].value - nodes[1].value
    if not logs:
        return None
    symbols = tuple(e[0] for e in logs)
    compiled = compile_values(
        [value, *(e[2] for e in logs)], atoms, denominators, extra_symbols=symbols
    )
    values, _, _ = compiled
    cancelled = cancellation(nodes, atoms, denominators, logs, values[1:], values[0])
    return nodes, logs, constants, compiled, cancelled
