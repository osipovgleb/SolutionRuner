"""Keep ratio domains and zero factors when reducing mixed trigonometric terms."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from ..word_problems.math_common import primitive
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_trigonometric_compile import C, S, T, U
from .trig_angles import C as NUMERIC_C
from .trig_angles import S as NUMERIC_S
from .trig_angles import multiple_angle


def compile_cotangent(values, atoms, denominators):
    if any(d.free_symbols for d in denominators):
        raise UnsupportedCondition("additional cotangent denominators are not reviewed")
    compiled = {}
    for symbol, atom in atoms.items():
        if atom.function == "ctg":
            if abs(atom.coefficient) != 1 or not atom.shift.is_Integer:
                raise UnsupportedCondition(
                    "cotangent requires one angle and integer-pi shifts"
                )
            compiled[symbol] = atom.coefficient * U
        elif atom.function in ("sin", "cos") and abs(atom.coefficient) <= 4:
            compiled[symbol] = multiple_angle(
                atom.function, atom.coefficient, int(2 * atom.shift)
            ).xreplace({NUMERIC_S: S, NUMERIC_C: C})
        else:
            raise UnsupportedCondition(
                "only cotangent with sine/cosine identities is reviewed"
            )
    raw = sp.expand((values[0] - values[1]).xreplace(compiled))
    reduced = sp.expand(sp.rem(raw, S * S + C * C - 1, C))
    if (
        reduced.has(S, C)
        or not reduced.is_polynomial(U)
        or reduced == 0
        or sp.degree(reduced, U) > 2
    ):
        raise UnsupportedCondition(
            "the cotangent identity must reduce to a nonzero quadratic"
        )
    identities = tuple(
        dict.fromkeys(
            (a.text.replace(r"\alpha", "x"), compiled[symbol])
            for symbol, a in atoms.items()
        )
    )
    return raw, identities


def ratio_branch(raw, variable):
    from .exam_trigonometric import Branch
    from .exam_trigonometric_inverse import angles, ordered

    reduced = sp.expand(sp.rem(raw, S * S + C * C - 1, C))
    if reduced.free_symbols != {variable}:
        raise UnsupportedCondition(
            "the ratio polynomial must not retain sine or cosine"
        )
    p = primitive(reduced, (variable,))
    values = roots(p.subs(variable, X))
    residues = ordered(q for v in values for q in angles(variable, v))
    return reduced, (Branch(variable, p, values, values, residues),)


def linear_branch(expression):
    from .exam_trigonometric import Branch
    from .exam_trigonometric_inverse import angles, ordered

    if (
        expression.free_symbols != {S, C}
        or sp.Poly(expression, S, C).total_degree() != 1
        or expression.subs({S: 0, C: 0}) != 0
    ):
        return None
    a, b = expression.coeff(S), expression.coeff(C)
    if a == 0 or b == 0:
        return None
    p = primitive(a * T + b, (T,))
    values = roots(p.subs(T, X))
    residues = ordered(q for v in values for q in angles(T, v))
    return Branch(T, p, values, values, residues, expression)


def cotangent_proof(a):
    from .exam_trigonometric_proof import candidate_lines, formula, polynomial

    html = "<p>Котангенс определён при условии:</p>" + line(r"\sin x\ne0")
    for text, value in a.identities:
        if text not in (r"\sin(x)", r"\cos(x)", r"\ctg(x)"):
            html += line(text + "=" + formula(value))
    html += line(formula(a.raw) + "=0")
    if a.raw != a.reduced:
        html += line(r"\sin^2 x+\cos^2 x=1")
        html += line(formula(a.reduced) + "=0")
    factors = sp.factor_list(a.reduced, U, extension=True)[1]
    full_square = len(factors) == 1 and factors[0][1] == 2
    if a.square and full_square:
        html += "<p>Получили полный квадрат:</p>" + line(
            formula(sp.factor(a.reduced, extension=True)) + "=0"
        )
        html += candidate_lines(a.branches[0])
    else:
        html += "<p>Решим полученное уравнение относительно котангенса:</p>"
        html += polynomial(a.branches[0])
    return (
        "<p>Применим формулу приведения и основное тригонометрическое тождество:</p>",
        html,
    )


def linear_proof(branch, angle):
    from .exam_trigonometric_proof import formula

    if branch.original is None:
        return ""
    return (
        "<p>Рассмотрим линейный множитель отдельно:</p>"
        + line(formula(branch.original, angle) + "=0")
        + "<p>При нулевом косинусе этот множитель не равен нулю: синус равен 1 или −1, а его коэффициент ненулевой. Поэтому только в этой ветви можно разделить на косинус:</p>"
        + line(r"\cos(" + angle + r")\ne0")
    )
