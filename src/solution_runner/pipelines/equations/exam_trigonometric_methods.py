"""Read parent methods and compile rational equations in a reviewed base angle."""

import re
from dataclasses import dataclass, replace

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .power_arithmetic import ScalarParser, clean
from .trig_angles import PI, multiple_angle
from .trig_angles import C as NUMERIC_C
from .trig_angles import S as NUMERIC_S
from .trig_symbolic_parser import (
    A,
    SymbolicAtom,
    SymbolicTrigonometricParser,
)


class ExamAngleParser(SymbolicTrigonometricParser):
    def _nested(self, text):
        return ExamAngleParser(
            text, self.atoms, self.denominators, self.depth + 1
        ).parse()

    def _atom(self, function, angle):
        variables = set(re.findall(r"\\(?:alpha|beta|gamma)", angle))
        if len(variables) != 1:
            raise UnsupportedCondition("one variable is required in each exam angle")
        variable = variables.pop()
        value = ScalarParser(
            clean(angle).replace(variable, "a").replace(r"\pi", "p"), {"a", "p"}
        ).parse()
        coefficient = sp.expand(value).coeff(A)
        shift = sp.cancel((value - coefficient * A) / PI)
        if (
            coefficient.is_Rational is not True
            or coefficient == 0
            or abs(coefficient) > 100
            or coefficient.q > 4
            or shift.is_Rational is not True
            or (12 * shift).is_Integer is not True
            or abs(shift) > 1000
        ):
            raise UnsupportedCondition(
                "bounded rational angle multiples and reviewed twelfth-pi shifts are required"
            )
        return sp.Symbol("T" + str(len(self.atoms)), real=True), SymbolicAtom(
            function, coefficient, shift, variable, "\\" + function + "(" + angle + ")"
        )


@dataclass(frozen=True)
class Equation:
    raw: sp.Expr
    identities: tuple
    scale: sp.Rational
    poles: tuple = ()
    reciprocal: sp.Expr | None = None
    doubled: bool = False


def shifted_atom(atom):
    sine = multiple_angle("sin", atom.coefficient, 0)
    cosine = multiple_angle("cos", atom.coefficient, 0)
    shift_sine, shift_cosine = sp.sin(atom.shift * sp.pi), sp.cos(atom.shift * sp.pi)
    return sp.expand(
        sine * shift_cosine + cosine * shift_sine
        if atom.function == "sin"
        else cosine * shift_cosine - sine * shift_sine
    )


def compile_reviewed(formula, preferred, preferred_scale):
    text = clean(formula).removesuffix(".")
    if text.count("=") != 1:
        raise UnsupportedCondition("one complete equation is required")
    atoms, denominators, values = {}, [], []
    for side in text.split("="):
        parser = ExamAngleParser(side.replace("x", r"\alpha"), atoms, denominators)
        values.append(parser.parse().value)
    if not atoms or any(a.function not in ("sin", "cos") for a in atoms.values()):
        raise UnsupportedCondition(
            "scaled rational equations require only sine and cosine"
        )
    scale = sp.gcd_list([abs(a.coefficient) for a in atoms.values()])
    for symbol, atom in tuple(atoms.items()):
        atoms[symbol] = replace(atom, coefficient=int(atom.coefficient / scale))
    if any(abs(a.coefficient) > 4 for a in atoms.values()):
        raise UnsupportedCondition("the base-angle multiple exceeds the reviewed range")
    compiled = {symbol: shifted_atom(atom) for symbol, atom in atoms.items()}
    convert = lambda v: sp.cancel(
        v.xreplace(compiled).xreplace({NUMERIC_S: S, NUMERIC_C: C})
    )
    expression = convert(values[0] - values[1])
    identities = tuple(
        dict.fromkeys(
            (a.text.replace(r"\alpha", "x"), convert(symbol))
            for symbol, a in atoms.items()
        )
    )
    original_poles = tuple(convert(d) for d in denominators if d.free_symbols)
    raw, denominator = sp.fraction(expression)
    if not original_poles and not denominator.free_symbols:
        raw = expression
    reciprocal = None
    if original_poles:
        variables = set().union(*(p.free_symbols for p in original_poles))
        if len(variables) == 1 and variables <= {S, C}:
            preferred = next(iter(variables))
        if scale != 1 or any(
            p.free_symbols != {preferred}
            or sp.Poly(p, preferred).degree() > 2
            or sp.Poly(p, preferred).length() != 1
            for p in original_poles
        ):
            raise UnsupportedCondition(
                "reciprocal substitution requires nonzero powers of one function"
            )
        t = sp.Symbol("t", real=True)
        reciprocal = sp.cancel(expression.subs(preferred, 1 / t))
        if not reciprocal.is_polynomial(t) or sp.degree(reciprocal, t) != 2:
            raise UnsupportedCondition(
                "the reciprocal substitution must produce a quadratic"
            )
    elif denominator.free_symbols:
        raise UnsupportedCondition("an original denominator must not be lost")
    if not raw.is_polynomial(S, C) or sp.Poly(raw, S, C).total_degree() > 4 or raw == 0:
        raise UnsupportedCondition(
            "a nonzero reviewed polynomial of degree at most four is required"
        )
    doubled = (
        preferred_scale == 2 * scale
        and preferred == C
        and all(
            all(n % 2 == 0 for n in powers) for powers in sp.Poly(raw, S, C).monoms()
        )
    )
    if doubled:
        reduced = sp.Poly(sp.rem(raw, S * S + C * C - 1, C), S)
        if any(power[0] % 2 for power, _ in reduced.terms()):
            raise UnsupportedCondition(
                "the double-angle method requires an even polynomial"
            )
        raw = sp.expand(
            sum(
                coef * ((1 - C) / 2) ** (power[0] // 2)
                for power, coef in reduced.terms()
            )
        )
        scale *= 2
        identities = ()
    return Equation(
        sp.expand(raw), identities, scale, original_poles, reciprocal, doubled
    )


def methods(parent_html):
    soup = BeautifulSoup(parent_html.replace("\xad", ""), "html.parser")
    markers = [
        n
        for n in soup.find_all(string=True)
        if "другое решение пункта а" in str(n).lower()
    ]
    if not markers:
        return parent_html, None
    if len(markers) != 1:
        raise UnsupportedCondition("one alternative first-part method is supported")
    node = markers[0].find_parent("p")
    if node is None or node.find("img"):
        raise UnsupportedCondition("a separate alternative-method heading is required")
    following = list(node.next_siblings)
    if any(
        getattr(n, "find", lambda *_: None)("img")
        for n in following
        if not isinstance(n, str)
    ):
        raise UnsupportedCondition(
            "an alternative figure needs its own reviewed placement"
        )
    alternative = "".join(str(n) for n in following)
    for n in following:
        n.extract()
    node.extract()
    return str(soup), alternative


def preference(parent_html):
    formulas = [
        "".join(s["data-inline-latex"].split())
        for s in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]")
    ]
    matches = []
    for formula in formulas:
        for match in re.finditer(
            r"\\(sin|cos|tg|ctg)(?:\^\{?(\d+)\}?)?(\d*)x&?=", formula
        ):
            right = re.split(
                r"\\\\|\\(?:iff|Leftrightarrow|end|quad|implies)",
                formula[match.end() :],
                maxsplit=1,
            )[0]
            if not re.search(r"\\(?:sin|cos|tg)", right):
                function, power, multiple = match.groups()
                matches.append((bool(power), function, sp.Rational(multiple or 1)))
    if not matches:
        raise UnsupportedCondition(
            "a trigonometric equation for the parent method is required"
        )
    _, function, multiple = min(
        enumerate(matches), key=lambda item: (item[1][0], item[0])
    )[1]
    return function, multiple


def factorized(parent_html):
    formulas = [
        "".join(s["data-inline-latex"].split())
        for s in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]")
    ]
    return any(
        re.search(r"\\(?:sin|cos)x\(", f)
        or re.search(
            r"\([^()]*\\(?:sin|cos)(?:\^\{?\d+\}?)?x[^()]*\)\([^()]*\\(?:sin|cos)(?:\^\{?\d+\}?)?x",
            f,
        )
        for f in formulas
    )
