"""Parent-style substitution, rational inequalities and physical interval selection."""

import re

import sympy as sp

from ..calculus.common import answer
from ..probability.common import line
from .fraction_questions import X

_PARAMETERS = {
    "train": {"frequency": "f_0", "sound": "c"},
    "short_circuit": {"internal": "r"},
    "parallel": {"resistance": "R_1"},
    "engine": {"cold": "T_2"},
    "load": {"internal": "r", "voltage": r"\epsilon"},
    "medium": {"frequency": "f_0", "receiver": "u", "source": "v"},
    "sonar": {"frequency": "f_0", "sound": "c"},
}


def substituted_formula(q):
    parameters = {
        label: sp.latex(q.values[key]) for key, label in _PARAMETERS[q.kind].items()
    }
    return re.sub(
        r"\\[a-zA-Z]+|[A-Za-z](?:_\d)?",
        lambda m: parameters.get(m[0], m[0]),
        q.formula,
    )


def final(a):
    q = a.question
    if q.relation == "eq":
        html = "<p>Полученное значение удовлетворяет уравнению и физическим ограничениям.</p>"
        label = q.label
    else:
        html = (
            "<p>Граничное значение входит в найденный промежуток и даёт искомое "
            + ("наибольшее" if q.maximum else "наименьшее")
            + " значение.</p>"
        )
        label = "{" + q.label + "}" + (r"_{\max}" if q.maximum else r"_{\min}")
    decimal = answer(a.result).replace(",", "{,}")
    return html + line(
        label
        + "="
        + sp.latex(a.result)
        + ("=" + decimal if a.result.is_Integer is not True else "")
        + r"\ \text{"
        + q.unit
        + "}"
    )


def proof(a):
    q = a.question

    def latex(expression):
        return sp.latex(expression, symbol_names={X: q.label})

    relation = {"eq": "=", "le": r"\leq", "ge": r"\geq"}[q.relation]
    html = (
        "<p>Подставим известные величины в формулу и учтём физические ограничения:</p>"
    )
    html += line(
        r",\quad ".join(
            label + "=" + latex(q.values[key])
            for key, label in _PARAMETERS[q.kind].items()
        )
    )
    html += line(q.label + r"\in" + latex(q.domain))
    if q.kind == "short_circuit":
        html += "<p>ЭДС положительна. Разделим ток на ток короткого замыкания, сократив общий множитель:</p>"
        html += line(
            r"\frac{I}{I_{\mathrm{кз}}}=\frac{\epsilon}{R+r}:\frac{\epsilon}{r}=\frac{r}{R+r}"
        )
        html += line(
            r"\frac{I}{I_{\mathrm{кз}}}"
            + relation
            + latex(q.values["target"])
            + r"\%=\frac{"
            + latex(q.values["target"])
            + "}{100}="
            + latex(q.target)
        )
    elif q.kind == "train":
        html += "<p>Разность частот должна быть не меньше указанной в условии:</p>"
        html += line(
            r"f(v)-f_0\geq"
            + latex(q.values["gap"])
            + r"\quad\Longleftrightarrow\quad f(v)\geq"
            + latex(q.target)
        )
    else:
        quantity = {
            "parallel": r"R_{\mathrm{общ}}",
            "engine": r"\eta",
            "load": "U",
            "medium": "f",
            "sonar": "v",
        }[q.kind]
        html += line(quantity + "=" + q.formula + (r"\%" if q.kind == "engine" else ""))
    html += line(
        (latex(q.expression) if q.kind == "short_circuit" else substituted_formula(q))
        + relation
        + latex(q.target)
    )
    numerator, denominator = sp.fraction(sp.cancel(q.expression - q.target))
    point = (
        q.domain.start + 1
        if q.domain.end is sp.oo
        else (q.domain.start + q.domain.end) / 2
    )
    if denominator.subs(X, point) < 0:
        numerator, denominator = -numerator, -denominator
    fraction = (
        r"\frac{"
        + latex(sp.factor(numerator))
        + "}{"
        + latex(sp.factor(denominator))
        + "}"
    )
    html += line(fraction + relation + "0")
    html += "<p>На допустимом промежутке знаменатель положителен, поэтому знак дроби определяется числителем:</p>"
    html += line(latex(sp.expand(numerator)) + relation + "0")
    html += line(q.label + r"\in" + latex(a.feasible))
    return html + final(a)
