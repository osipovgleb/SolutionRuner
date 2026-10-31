"""Factor a double-angle identity while retaining original tangent poles."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, T, U

X = sp.Symbol("x", real=True)
H = sp.Symbol("h", real=True)


@dataclass(frozen=True)
class RatioProduct:
    angle: int
    level: sp.Expr
    coefficient: sp.Expr
    method: str


def style(html):
    soup = BeautifulSoup(html, "html.parser")
    formulas = " ".join(
        n["data-inline-latex"] for n in soup.select("[data-inline-latex]")
    )
    formulas = re.sub(r"\\operatorname\{(tg|ctg)\}", r"\\\1", "".join(formulas.split()))
    text = soup.get_text(" ").replace("\xad", "").lower()
    if not re.search(r"\\sin\^\{?2\}?\d*x", formulas):
        return None
    if "умножив обе части уравнения на" in text and r"1-\cos" in formulas:
        return "multiply"
    if r"\ctg" in formulas and re.search(r"\\sin\^\{?2\}?\d*x\([^()]*\\tg", formulas):
        return "factor"
    return None


def compile_product(formula, method):
    from .exam_trigonometric_methods import Equation, constant_angles, parse_equation

    values, atoms, denominators = parse_equation(formula)
    values, atoms, denominators, _ = constant_angles(values, atoms, denominators)
    sine_angles = {a.coefficient for a in atoms.values() if a.function == "sin"}
    if (
        method not in ("multiply", "factor")
        or len(sine_angles) != 1
        or denominators
        or any(a.shift != 0 for a in atoms.values())
    ):
        raise UnsupportedCondition(
            "the ratio product needs one unshifted sine angle and no extra denominator"
        )
    angle = sine_angles.pop()
    if angle not in (2, 3, 4, 6):
        raise UnsupportedCondition(
            "the reviewed ratio product uses a double, triple, quadruple or sixth angle"
        )
    compiled = {}
    functions = set()
    for symbol, atom in atoms.items():
        expected = {
            "sin": (angle, H),
            "cos": (2 * angle, 1 - 2 * H * H),
            "tg": (1, T),
            "ctg": (1, U),
        }
        if (
            atom.function not in expected
            or atom.coefficient != expected[atom.function][0]
        ):
            raise UnsupportedCondition(
                "the ratio product angles must match the double-angle identity"
            )
        compiled[symbol] = expected[atom.function][1]
        functions.add(atom.function)
    if functions != {"sin", "cos", "tg", "ctg"}:
        raise UnsupportedCondition(
            "both original tangent and cotangent domains are required"
        )
    raw = sp.expand((values[0] - values[1]).xreplace(compiled))
    factor = sp.cancel(raw / (H * H))
    coefficient, other = factor.coeff(T), factor.coeff(U)
    if not coefficient or sp.expand(factor - coefficient * T - other * U) != 0:
        raise UnsupportedCondition(
            "the folded sine square must multiply one tangent-cotangent difference"
        )
    level = sp.cancel(-other / coefficient)
    if level.is_positive is not True or level.free_symbols or coefficient.free_symbols:
        raise UnsupportedCondition(
            "the squared tangent level must be a positive constant"
        )
    from .exam_trigonometric_inverse import angles

    angles(T, sp.sqrt(level))
    actual = sp.sin(angle * X) ** 2 * (coefficient * sp.tan(X) + other * sp.cot(X))
    return Equation(
        actual,
        (),
        sp.S.One,
        poles=(S, C),
        ratio_product=RatioProduct(int(angle), level, coefficient, method),
    )


def branches(data):
    from .exam_trigonometric import Branch, solve_branches
    from .exam_trigonometric_domain import without_poles

    ratio = solve_branches(T * T - data.level, T)[1]
    if data.method == "multiply":
        zero = Branch(
            S,
            S,
            (sp.S.Zero,),
            (sp.S.Zero,),
            tuple(sp.Rational(k, data.angle) for k in range(2 * data.angle)),
            angle_scale=sp.Integer(data.angle),
        )
        result = (zero, *ratio)
    else:
        polynomial = sp.chebyshevu(data.angle - 1, C)
        while polynomial.subs(C, 0) == 0:
            polynomial = sp.cancel(polynomial / C)
        zero = solve_branches(polynomial, C)[1] if polynomial.has(C) else ()
        result = (*zero, *ratio)
    return without_poles(result, (S, C))


def proof(a):
    from .exam_trigonometric_proof import families, formula, polynomial
    from .exam_trigonometric_variants import argument

    data = a.ratio_product
    angle, twice = argument(data.angle), argument(2 * data.angle)
    html = line(
        r"\sin x\ne0,\quad\cos x\ne0\quad\Longleftrightarrow\quad x\ne\frac{\pi n}{2},\ n\in\mathbb Z"
    )
    html += line(a.original)
    if data.method == "multiply":
        html += "<p>На области определения тангенс ненулевой. Умножим обе части на него:</p>"
        html += line(
            r"\frac{"
            + sp.latex(data.coefficient)
            + r"}{2}(1-\cos("
            + twice
            + r"))\tg^2x="
            + sp.latex(data.coefficient * data.level)
            + r"\sin^2("
            + angle
            + ")"
        )
    html += "<p>Применим формулу двойного угла:</p>"
    html += line(r"1-\cos(" + twice + r")=2\sin^2(" + angle + ")")
    if data.method == "factor":
        html += line(
            r"\sin^2(" + angle + r")(\tg x-" + sp.latex(data.level) + r"\ctg x)=0"
        )
        html += "<p>Умножение на ненулевой тангенс сохраняет равносильность. Разложим синус кратного угла:</p>"
        html += line(
            r"\sin(" + angle + ")=" + formula(S * sp.chebyshevu(data.angle - 1, C))
        )
        html += line(
            formula(sp.factor(sp.chebyshevu(data.angle - 1, C)))
            + r"=0\quad\text{или}\quad\tg^2x="
            + sp.latex(data.level)
        )
    else:
        html += line(r"\sin^2(" + angle + r")(\tg^2x-" + sp.latex(data.level) + ")=0")
        html += line(
            r"\sin("
            + angle
            + r")=0\quad\Longleftrightarrow\quad x=\frac{\pi k}{"
            + str(data.angle)
            + r"},\ k\in\mathbb Z"
        )
    html += "<p>Сохраним обе ветви и исключим все точки, запрещённые исходной областью определения:</p>"
    for branch in a.branches:
        if data.method == "multiply" and branch.variable == S:
            continue
        html += polynomial(branch)
    html += "<p>С учётом исходной области определения остаются серии:</p>"
    for text in families(a):
        html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Запишем область определения до умножения и сокращений:</p>", html


def series(branches):
    result = []
    for branch in branches:
        offsets = sorted({q % 1 for q in branch.residues})
        for q in offsets:
            result.append((q - 1 if q > sp.Rational(1, 2) else q, sp.S.One))
    return tuple(dict.fromkeys(result))
