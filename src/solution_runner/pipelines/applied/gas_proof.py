"""Parent-style invariants and raising positive sides to reciprocal powers."""

import sympy as sp

from ..calculus.common import answer
from ..probability.common import line


def final(a, label, unit=""):
    decimal = answer(a.result).replace(",", "{,}")
    return line(
        label
        + "="
        + sp.latex(a.result)
        + ("=" + decimal if a.result.is_Integer is not True else "")
        + (r"\ " + unit if unit else "")
    )


def absolute(a):
    v = a.question.values
    source = a.question.source
    exponent = sp.latex(v["exponent"])
    html = "<p>Произведение давления на степень положительного объёма постоянно. Подставим давление и разделим обе части равенства на него:</p>"
    html += line("pV^{" + exponent + "}=" + source["constant"])
    html += line(
        "(" + source["pressure"] + ")V^{" + exponent + "}=" + source["constant"]
    )
    html += line(
        "V^{"
        + exponent
        + r"}=\frac{"
        + source["constant"]
        + "}{"
        + source["pressure"]
        + "}="
        + sp.latex(a.ratio)
    )
    html += "<p>Объём положителен, поэтому возводим обе части в обратную степень:</p>"
    html += line(
        "V=\\left("
        + sp.latex(a.ratio)
        + r"\right)^{"
        + sp.latex(1 / v["exponent"])
        + "}"
    )
    return html + final(a, "V", r"\mathrm{м}^3")


def compression(a):
    q = a.question
    v = q.values
    k = sp.latex(v["exponent"])
    relation = r"\leq" if q.kind == "compression_min" else "="
    reverse = r"\geq" if q.kind == "compression_min" else "="
    html = "<p>Обозначим начальные давление и объём через p₁ и V₁, конечные — через p₂ и V₂. Для положительных объёмов выполняется:</p>"
    html += line("k=" + q.source["exponent"] + "=" + k)
    html += line("p_1V_1^{" + k + "}=p_2V_2^{" + k + "}")
    html += line(
        r"p_1=1,\quad V_1="
        + sp.latex(v["initial"])
        + r",\quad p_2"
        + relation
        + sp.latex(v["pressure"])
    )
    html += line(
        r"\left(\frac{V_1}{V_2}\right)^{" + k + "}" + relation + sp.latex(v["pressure"])
    )
    html += "<p>Возведём положительные части в обратную степень и выразим конечный объём:</p>"
    html += line(
        r"\frac{V_1}{V_2}"
        + relation
        + "("
        + sp.latex(v["pressure"])
        + ")^{"
        + sp.latex(1 / v["exponent"])
        + "}="
        + sp.latex(a.ratio)
    )
    html += line(
        "V_2"
        + reverse
        + r"\frac{"
        + sp.latex(v["initial"])
        + "}{"
        + sp.latex(a.ratio)
        + "}"
    )
    if q.kind == "compression_min":
        html += "<p>При уменьшении объёма давление растёт. Граничное значение давления допускается, поэтому полученная граница — наименьший объём.</p>"
    return html + final(
        a, r"{V_2}_{\min}" if q.kind == "compression_min" else "V_2", r"\text{л}"
    )


def factor(a):
    v = a.question.values
    pressure = r"\frac{p_2}{p_1}" if v["compression"] else r"\frac{p_1}{p_2}"
    volume = r"\frac{V_1}{V_2}" if v["compression"] else r"\frac{V_2}{V_1}"
    html = "<p>Пусть p₁, V₁ — начальные давление и объём, а p₂, V₂ — конечные. Запишем постоянство произведения:</p>"
    html += line(r"p_1V_1^a=p_2V_2^a")
    html += line(pressure + "=" + volume + "^a")
    html += line(
        volume
        + "="
        + sp.latex(v["volume_factor"])
        + r",\quad "
        + pressure
        + r"\geq"
        + sp.latex(v["pressure_factor"])
    )
    html += line(
        "(" + sp.latex(v["volume_factor"]) + r")^a\geq" + sp.latex(v["pressure_factor"])
    )
    html += line(
        sp.latex(v["pressure_factor"])
        + "=("
        + sp.latex(v["volume_factor"])
        + ")^{"
        + sp.latex(a.result)
        + "}"
    )
    html += "<p>Основание больше единицы, поэтому показательная функция возрастает:</p>"
    html += line(r"a\geq" + sp.latex(a.result))
    return html + final(a, r"a_{\min}")


def proof(a):
    return {
        "absolute": absolute,
        "factor": factor,
        "compression_min": compression,
        "compression_equal": compression,
    }[a.question.kind](a)
