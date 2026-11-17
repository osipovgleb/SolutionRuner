"""Parse reviewed symbolic angles in exam trigonometric equations."""

import re

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .power_arithmetic import ScalarParser, clean
from .trig_angles import PI, parse_angle
from .trig_symbolic_parser import A, SymbolicAtom, SymbolicTrigonometricParser


class ExamAngleParser(SymbolicTrigonometricParser):
    allowed_powers = (1, 2, 3, 4, 6)

    def _angle(self):
        decimal = re.match(
            r"[+-]?\d+\.\d+\\(?:alpha|beta|gamma)", self.text[self.index :]
        )
        if decimal:
            self.index += decimal.end()
            return decimal.group()
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
                or (
                    (12 * shift).is_Integer is not True
                    and (8 * shift).is_Integer is not True
                )
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
            or (
                (12 * shift).is_Integer is not True
                and (8 * shift).is_Integer is not True
            )
            or abs(shift) > 10000
        ):
            raise UnsupportedCondition(
                "bounded rational angle multiples and reviewed eighth- or twelfth-pi shifts are required"
            )
        return sp.Symbol("T" + str(len(self.atoms)), real=True), SymbolicAtom(
            function,
            coefficient.subs(PI, sp.pi),
            shift,
            variable,
            "\\" + function + "(" + angle + ")",
        )
