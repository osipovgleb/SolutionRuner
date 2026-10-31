"""Read parent methods and compile rational equations in a reviewed base angle."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, T
from .exam_trigonometric_homogeneous import Reduction
from .power_arithmetic import ScalarParser, clean
from .trig_angles import PI, multiple_angle, parse_angle
from .trig_angles import C as NUMERIC_C
from .trig_angles import S as NUMERIC_S
from .trig_symbolic_parser import (
    A,
    SymbolicAtom,
    SymbolicTrigonometricParser,
)

if TYPE_CHECKING:
    from .exam_trigonometric_affine import AffineFactor
    from .exam_trigonometric_angle_product import AngleProduct
    from .exam_trigonometric_ratio_product import RatioProduct
    from .exam_trigonometric_square_difference import SquareDifference
    from .exam_trigonometric_sum_product import SumProduct
    from .exam_trigonometric_symmetric import SumReduction
    from .exam_trigonometric_triple_angle import TripleAngle


class ExamAngleParser(SymbolicTrigonometricParser):
    allowed_powers = (1, 2, 3, 4, 6)

    def _angle(self):
        match = re.match(r"[+-]?(?:\d+)?\\pi\\alpha", self.text[self.index :])
        if match:
            self.index += match.end()
            return match.group()
        return super()._angle()

    def _nested(self, text):
        return ExamAngleParser(
            text, self.atoms, self.denominators, self.depth + 1
        ).parse()

    def _atom(self, function, angle):
        variables = set(re.findall(r"\\(?:alpha|beta|gamma)", angle))
        if not variables:
            shift, degrees = parse_angle(angle)
            if (
                degrees
                or (12 * shift).is_Integer is not True
                or function not in ("sin", "cos")
            ):
                raise UnsupportedCondition(
                    "a reviewed constant sine or cosine coefficient is required"
                )
            return sp.Symbol("T" + str(len(self.atoms)), real=True), SymbolicAtom(
                function,
                sp.S.Zero,
                shift,
                r"\alpha",
                "\\" + function + "(" + angle + ")",
            )
        if len(variables) != 1:
            raise UnsupportedCondition("one variable is required in each exam angle")
        variable = variables.pop()
        value = ScalarParser(
            clean(angle).replace(variable, "a").replace(r"\pi", "p"), {"a", "p"}
        ).parse()
        coefficient = sp.expand(value).coeff(A)
        shift = sp.cancel((value - coefficient * A) / PI)
        multiple = sp.cancel(coefficient / PI) if coefficient.has(PI) else coefficient
        if (
            multiple.is_Rational is not True
            or multiple == 0
            or abs(multiple) > 100
            or multiple.q > 4
            or shift.is_Rational is not True
            or (12 * shift).is_Integer is not True
            or abs(shift) > 10000
        ):
            raise UnsupportedCondition(
                "bounded rational angle multiples and reviewed twelfth-pi shifts are required"
            )
        return sp.Symbol("T" + str(len(self.atoms)), real=True), SymbolicAtom(
            function,
            coefficient.subs(PI, sp.pi),
            shift,
            variable,
            "\\" + function + "(" + angle + ")",
        )


@dataclass(frozen=True)
class Equation:
    raw: sp.Expr
    identities: tuple
    scale: sp.Expr
    poles: tuple = ()
    reciprocal: sp.Expr | None = None
    doubled: bool = False
    rewritten: sp.Expr | None = None
    domain: sp.Expr | None = None
    strict_domain: bool = False
    fraction: sp.Expr | None = None
    absolute: tuple | None = None
    homogeneous: Reduction | None = None
    power_angle: sp.Rational | None = None
    affine: "AffineFactor | None" = None
    factored_source: sp.Expr | None = None
    angle_product: "AngleProduct | None" = None
    cleared_denominator: sp.Expr | None = None
    square_difference: "SquareDifference | None" = None
    symmetric: "SumReduction | None" = None
    square_product: tuple | None = None
    unit_factors: tuple | None = None
    sum_product: "SumProduct | None" = None
    triple_angle: "TripleAngle | None" = None
    ratio_product: "RatioProduct | None" = None


def shifted_atom(atom):
    sine = multiple_angle("sin", atom.coefficient, 0)
    cosine = multiple_angle("cos", atom.coefficient, 0)
    shift_sine, shift_cosine = sp.sin(atom.shift * sp.pi), sp.cos(atom.shift * sp.pi)
    return sp.expand(
        sine * shift_cosine + cosine * shift_sine
        if atom.function == "sin"
        else cosine * shift_cosine - sine * shift_sine
    )


def parse_equation(formula):
    text = clean(formula).removesuffix(".")
    if text.count("=") != 1:
        raise UnsupportedCondition("one complete equation is required")
    atoms, denominators, values = {}, [], []
    for side in text.split("="):
        parser = ExamAngleParser(side.replace("x", r"\alpha"), atoms, denominators)
        values.append(parser.parse().value)
    if any(a.variable != r"\alpha" for a in atoms.values()):
        raise UnsupportedCondition("the exam equation must use one x variable")
    return values, atoms, denominators


def compile_reviewed(
    formula,
    preferred,
    preferred_scale,
    translation=sp.S.Zero,
    difference=False,
    preserve_products=False,
):
    from .exam_trigonometric_affine import reviewed as affine_equation

    affine = affine_equation(formula, preferred_scale, translation)
    if affine is not None:
        return affine
    values, atoms, denominators, constants = read_translated_equation(
        formula, translation
    )
    from .exam_trigonometric_square_difference import compile_difference

    squared = (
        compile_difference(values, atoms, denominators)
        if difference and not translation
        else None
    )
    if squared is not None:
        return squared
    if difference:
        raise UnsupportedCondition(
            "the parent's square-difference method requires two compatible nondegenerate squares"
        )
    if any(a.function in ("tg", "ctg") for a in atoms.values()):
        from .exam_trigonometric_ratios import compile_ratio_method

        return compile_ratio_method(values, atoms, denominators, preferred, constants)
    if not atoms or any(a.function not in ("sin", "cos") for a in atoms.values()):
        raise UnsupportedCondition(
            "scaled rational equations require only sine and cosine"
        )
    from .exam_trigonometric_folding import normalize_base

    values, atoms, scale, unit, preferred_scale, rewritten, power_angle = (
        normalize_base(
            values, atoms, denominators, preferred, preferred_scale, preserve_products
        )
    )
    if any(abs(a.coefficient) > 4 for a in atoms.values()):
        if translation or unit != 1:
            raise UnsupportedCondition(
                "separate angle factors require the original radian variable"
            )
        from .exam_trigonometric_angle_product import compile_product

        return compile_product(formula)
    compiled, expression, identities, original_poles = polynomial_input(
        values, atoms, denominators
    )
    if original_poles and (
        expression.is_polynomial(S, C)
        or any(
            len(p.free_symbols) != 1 or sp.Poly(p, *p.free_symbols).length() != 1
            for p in original_poles
        )
    ):
        from .exam_trigonometric_rational import compile_fraction

        return compile_fraction(
            values, compiled, original_poles, scale, constants + identities
        )
    raw, denominator = sp.fraction(expression)
    if not original_poles and not denominator.free_symbols:
        raw = expression
    reciprocal = None
    if original_poles:
        if preferred != T:
            reciprocal, preferred = reciprocal_polynomial(
                expression, original_poles, scale, preferred
            )
    elif denominator.free_symbols:
        raise UnsupportedCondition("an original denominator must not be lost")
    raw, scale, doubled = reduce_base_angle(raw, scale, preferred, preferred_scale)
    if doubled:
        identities = ()
    return Equation(
        sp.expand(raw),
        constants + identities,
        scale * unit,
        original_poles,
        reciprocal,
        doubled,
        rewritten,
        power_angle=power_angle,
    )


def polynomial_input(values, atoms, denominators):
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
    return compiled, expression, identities, original_poles


def read_translated_equation(formula, translation):
    values, atoms, denominators = parse_equation(formula)
    values, atoms, denominators, constants = constant_angles(
        values, atoms, denominators
    )
    if translation:
        from .exam_trigonometric_translation import translated_atoms

        atoms = translated_atoms(atoms, translation)
    return values, atoms, denominators, constants


def reciprocal_polynomial(expression, original_poles, scale, preferred):
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
    return reciprocal, preferred


def constant_angles(values, atoms, denominators):
    constants = {
        s: (sp.sin if a.function == "sin" else sp.cos)(a.shift * sp.pi)
        for s, a in atoms.items()
        if a.coefficient == 0
    }
    identities = tuple((atoms[s].text, value) for s, value in constants.items())
    denominators = [value.xreplace(constants) for value in denominators]
    if any(value == 0 for value in denominators):
        raise UnsupportedCondition("a constant trigonometric denominator is zero")
    return (
        [value.xreplace(constants) for value in values],
        {s: a for s, a in atoms.items() if s not in constants},
        denominators,
        identities,
    )


def reduce_base_angle(raw, scale, preferred, preferred_scale):
    if not raw.is_polynomial(S, C) or sp.Poly(raw, S, C).total_degree() > 8 or raw == 0:
        raise UnsupportedCondition(
            "a nonzero bounded polynomial is required before base-angle reduction"
        )
    raw, scale, doubled = double_angle(raw, scale, preferred, preferred_scale)
    if sp.Poly(raw, S, C).total_degree() > 4:
        raise UnsupportedCondition(
            "the final base-angle polynomial exceeds degree four"
        )
    return raw, scale, doubled


def double_angle(raw, scale, preferred, preferred_scale):
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
    return raw, scale, doubled


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
            r"\\(sin|cos|tg|ctg)(?:\^\{?(\d+)\}?)?(?:(\d*)(\\pi)?x|\\frac\{(\d*)x\}\{(\d+)\})&?=",
            formula,
        ):
            right = re.split(
                r"\\\\|\\(?:iff|Leftrightarrow|end|quad|implies)",
                formula[match.end() :],
                maxsplit=1,
            )[0]
            if not re.search(r"\\(?:sin|cos|tg)", right):
                function, power, multiple, pi_unit, numerator, denominator = (
                    match.groups()
                )
                scale = (
                    sp.Rational(numerator or 1, denominator)
                    if denominator
                    else sp.Rational(multiple or 1)
                )
                if pi_unit:
                    scale *= sp.pi
                matches.append((bool(power), function, scale))
    if not matches:
        from .exam_trigonometric_sum_identities import style as sum_style

        if sum_style(parent_html) == "constant_sum":
            return "sin", sp.S.One
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
    formulas = [re.sub(r"\\frac\{\d*x\}\{\d+\}", "x", f) for f in formulas]
    formulas = [
        re.sub(r"\\(sin|cos)(\d+)(?:\\pi)?x", lambda m: "\\" + m[1] + "x", f)
        for f in formulas
    ]
    return any(
        re.search(r"\\(?:sin|cos)x(?:\\cdot)?\(", f)
        or re.search(
            r"\([^()]*\\(?:sin|cos|tg)(?:\^\{?\d+\}?)?x[^()]*\)\([^()]*\\(?:sin|cos|tg)(?:\^\{?\d+\}?)?x",
            f,
        )
        for f in formulas
    )
