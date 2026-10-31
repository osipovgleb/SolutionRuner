"""Keep direct substitution, inverse equations and both parent range methods."""

from ..probability.common import line
from ..word_problems.motion_chase_proof import section
from .explog_coefficients import (
    coefficients,
    exponential_range,
    formula,
    logarithm,
    n,
    power,
)
from .explog_models import exact_log


def evaluate(a):
    q, b = a.question, a.shift
    t, r = q.target, a.result
    html = "<p>Значит, получаем формулу функции:</p>" + line("f(x)=" + formula(a))
    if q.mode == "value":
        html += "<p>Найдём значение функции при указанном аргументе:</p>"
        html += line("f(" + n(t) + ")=" + formula(a, n(t)))
        if q.model.startswith("log"):
            argument = t + b if q.model == "log_horizontal" else t
            exponent = exact_log(argument, a.base)
            html += line(
                n(argument)
                + "="
                + power(a.base, n(exponent))
                + r",\qquad"
                + logarithm(a.base, n(argument))
                + "="
                + n(exponent)
            )
            result_step = (
                n(exponent)
                if q.model == "log_horizontal"
                else n(b) + "+(" + n(exponent) + ")"
            )
        else:
            exponent = t + b if q.model == "exp_horizontal" else t
            value = a.base**exponent
            if exponent < 0:
                html += line(
                    power(a.base, n(exponent))
                    + r"=\frac{1}{"
                    + power(a.base, n(-exponent))
                    + "}="
                    + n(value)
                )
            else:
                html += line(power(a.base, n(exponent)) + "=" + n(value))
            result_step = n(value) + (
                "+(" + n(b) + ")" if q.model == "exp_vertical" else ""
            )
        return html + line(
            "f("
            + n(t)
            + ")="
            + result_step
            + ("=" + n(r) if result_step != n(r) else "")
        )
    html += "<p>Решим уравнение для указанного значения функции:</p>" + line(
        formula(a) + "=" + n(t)
    )
    if q.model.startswith("log"):
        exponent = t if q.model == "log_horizontal" else t - b
        left = "x+(" + n(b) + ")" if q.model == "log_horizontal" else "x"
        html += line(logarithm(a.base, left) + "=" + n(exponent))
        html += line(
            left + "=" + power(a.base, n(exponent)) + "=" + n(a.base**exponent)
        )
        return html + (line("x=" + n(r)) if left != "x" else "")
    value = t - b if q.model == "exp_vertical" else t
    exponent = exact_log(value, a.base)
    left = "x+(" + n(b) + ")" if q.model == "exp_horizontal" else "x"
    html += line(
        power(a.base, left) + "=" + n(value) + "=" + power(a.base, n(exponent))
    )
    html += "<p>При положительном основании, не равном единице, равенство степеней означает равенство показателей:</p>"
    return html + line(
        left + "=" + n(exponent) + (r",\qquad x=" + n(r) if left != "x" else "")
    )


def proof(a):
    first = coefficients(a) + evaluate(a)
    html = section(first, "Решение")
    if a.question.model == "exp_vertical" and a.question.mode == "argument":
        html += section(exponential_range(a) + evaluate(a), "Приведём другое решение.")
    return html
