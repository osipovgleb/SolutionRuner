"""Parent-style normalization and explicit substitution into rating formulas."""

import sympy as sp

from ..probability.common import line


def display(formula):
    return formula.replace("r_b", r"r_{\mathrm{пок}}").replace(
        "r_e", r"r_{\mathrm{экс}}"
    )


def weighted(a):
    q, v = a.question, a.question.values
    total = sum(v["weights"])
    labels = "In=Op=Tr" + ("=Q" if q.kind != "three_max" else "")
    html = "<p>Нормировочный множитель A положителен. Подставим в формулу значения показателей:</p>"
    html += line("A>0,\\qquad R=" + q.formula)
    if q.kind == "identity":
        html += line(
            labels
            + r"=x,\quad x\in\mathbb Z\cap["
            + sp.latex(v["lower"])
            + ";"
            + sp.latex(v["upper"])
            + "]"
        )
        terms = "+".join((str(w) if w != 1 else "") + "x" for w in v["weights"] if w)
        html += line(r"R=\frac{" + terms + r"}{A}=\frac{" + str(total) + "x}{A}")
        html += "<p>Равенство должно выполняться для каждой допустимой оценки, в том числе ненулевой. Для неё можно сократить x; при нулевой оценке равенство затем также верно:</p>"
        html += line(
            r"\frac{"
            + str(total)
            + r"x}{A}=x\quad\Longrightarrow\quad A="
            + sp.latex(a.result)
        )
        return html + line(
            r"R=\frac{" + str(total) + "x}{" + sp.latex(a.result) + "}=x"
        )
    maximum = sp.latex(v["upper"])
    html += line(labels + "=" + maximum)
    terms = "+".join(str(w) + r"\cdot(" + maximum + ")" for w in v["weights"] if w)
    html += line(r"R=\frac{" + terms + r"}{A}=\frac{" + sp.latex(a.numerator) + "}{A}")
    html += "<p>Приравняем полученный рейтинг к заданному и найдём A:</p>"
    html += line(sp.latex(v["target"]) + r"=\frac{" + sp.latex(a.numerator) + "}{A}")
    html += line(sp.latex(v["target"]) + "A=" + sp.latex(a.numerator))
    return html + line(
        r"A=\frac{"
        + sp.latex(a.numerator)
        + "}{"
        + sp.latex(v["target"])
        + "}="
        + sp.latex(a.result)
    )


def store(a):
    q, v = a.question, a.question.values
    k, buyer, expert = (sp.latex(v[key]) for key in ["count", "buyer", "expert"])
    html = "<p>Подставим заданные оценки и число покупателей. Сначала вычислим знаменатель дроби в формуле рейтинга:</p>"
    factor = r"\frac{0{,}02\cdot(" + k + ")}{(" + buyer + r")+0{,}1}"
    if q.kind == "store_power":
        html += line(display(r"m=\frac{0{,}02K}{r_b+0{,}1}"))
        html += line("m=" + factor + "=" + sp.latex(a.exponent))
        html += line(
            r"D=(K+1)^m=("
            + k
            + "+1)^{"
            + sp.latex(a.exponent)
            + "}="
            + sp.latex(a.denominator)
        )
    else:
        html += line(display(r"D=(K+1)\frac{0{,}02K}{r_b+0{,}1}"))
        html += line("D=(" + k + "+1)" + factor)
        html += line(
            "D=("
            + k
            + "+1)"
            + r"\cdot("
            + sp.latex(a.exponent)
            + ")="
            + sp.latex(a.denominator)
        )
    html += "<p>Теперь вычислим сам рейтинг по исходной формуле:</p>"
    html += line("R=" + display(q.formula))
    html += line(
        "R=("
        + buyer
        + r")-\frac{("
        + buyer
        + ")-("
        + expert
        + ")}{"
        + sp.latex(a.denominator)
        + "}"
    )
    html += line(
        "R=("
        + buyer
        + r")-\frac{"
        + sp.latex(a.numerator)
        + "}{"
        + sp.latex(a.denominator)
        + "}"
    )
    return html + line("R=" + sp.latex(a.result))


def proof(a):
    return store(a) if a.question.kind.startswith("store_") else weighted(a)
