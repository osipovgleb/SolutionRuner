"""Parent-style isolation of a scalar and interval selection for revenue or inertia."""

import sympy as sp

from ..calculus.common import answer
from ..probability.common import line


def latex(q, expression):
    return sp.latex(expression, symbol_names={q.variable: q.label})


def given(q, key):
    return q.source_values[key].replace(" ", "")


def final(a, maximum=False, minimum=False):
    q = a.question
    label = "{" + q.label + "}" if "_" in q.label and (maximum or minimum) else q.label
    label += r"_{\max}" if maximum else r"_{\min}" if minimum else ""
    unit = q.unit if q.kind == "thermal" else r"\text{" + q.unit + "}"
    fraction = latex(q, a.result)
    decimal = answer(a.result).replace(",", "{,}")
    return line(
        label
        + "="
        + fraction
        + ("=" + decimal if a.result.is_Integer is not True else "")
        + r"\ "
        + unit
    )


def thermal(a):
    q = a.question
    html = "<p>Удлинение равно разности новой и исходной длины. Переведём миллиметры в метры:</p>"
    html += line(
        r"\Delta l="
        + given(q, "increase")
        + r"\cdot10^{-3}="
        + latex(q, q.target)
        + r"\ \text{м}"
    )
    html += "<p>Подставим закон теплового расширения и выразим температуру:</p>"
    html += line(r"l(t)-l_0=\Delta l")
    html += line(r"l_0(1+\alpha t)-l_0=\Delta l")
    html += line(r"l_0\alpha t=\Delta l")
    html += line(
        given(q, "length")
        + r"\cdot("
        + given(q, "alpha")
        + r")\cdot t="
        + latex(q, q.target)
    )
    html += line(
        "t="
        + r"\frac{"
        + latex(q, q.target)
        + "}{"
        + given(q, "length")
        + r"\cdot("
        + given(q, "alpha")
        + ")}"
    )
    return html + final(a)


def profit(a):
    q = a.question
    v = q.values
    margin = v["price"] - v["cost"]
    html = "<p>Приравняем месячную операционную прибыль требуемому значению и выразим объём производства:</p>"
    html += line(r"\pi(q)=q(p-v)-f")
    html += line(
        "q("
        + given(q, "price")
        + "-"
        + given(q, "cost")
        + ")-"
        + given(q, "overhead")
        + "="
        + latex(q, q.target)
    )
    html += line(
        latex(q, margin) + "q=" + latex(q, q.target) + "+" + given(q, "overhead")
    )
    html += line(latex(q, margin) + "q=" + latex(q, q.target + v["overhead"]))
    html += line(
        r"q=\frac{" + latex(q, q.target + v["overhead"]) + "}{" + latex(q, margin) + "}"
    )
    html += "<p>Полученное количество единиц продукции неотрицательно и целое.</p>"
    return html + final(a)


def interval_steps(a):
    q = a.question
    equation = (
        sp.Poly(a.expression - q.target, q.variable)
        .clear_denoms(convert=True)[1]
        .primitive()[1]
    )
    if equation.LC() < 0:
        equation = -equation
    relation = "=" if q.relation == "eq" else r"\leq"
    html = line(latex(q, equation.as_expr()) + relation + "0")
    html += line(latex(q, sp.factor(equation.as_expr())) + relation + "0")
    html += line(
        r";\quad ".join(
            q.label + "_{" + str(i) + "}=" + latex(q, r)
            for i, r in enumerate(a.roots, 1)
        )
    )
    return html


def market(a):
    q = a.question
    relation = "=" if q.relation == "eq" else r"\geq"
    html = "<p>Выручка равна произведению цены на объём спроса. Подставим зависимость спроса:</p>"
    html += line("q(p)=" + latex(q, q.demand))
    html += line("r(p)=p\\cdot q(p)=" + latex(q, a.expression))
    html += "<p>Учитываем неотрицательность цены и спроса:</p>"
    html += line(
        r"p\geq0,\quad q(p)\geq0\quad\Longrightarrow\quad p\in[0;"
        + latex(q, a.domain_end)
        + "]"
    )
    html += (
        "<p>Решим требуемое "
        + ("уравнение" if q.relation == "eq" else "неравенство")
        + ":</p>"
    )
    html += line("r(p)" + relation + latex(q, q.target))
    html += interval_steps(a)
    if q.relation == "ge":
        html += line(
            r"p\in[" + latex(q, min(a.roots)) + ";" + latex(q, max(a.roots)) + "]"
        )
    html += "<p>Среди допустимых цен выбираем наибольшую:</p>"
    return html + final(a, maximum=True)


def inertia(a):
    q = a.question
    html = (
        "<p>Подставим массы и радиус в формулу момента инерции и решим неравенство:</p>"
    )
    html += line(r"I=\frac{(m+2M)R^2}{2}+M(2Rh+h^2)")
    html += line(
        r"I=\frac{("
        + given(q, "mass")
        + "+2\\cdot"
        + given(q, "side")
        + ")\\cdot("
        + given(q, "radius")
        + r")^2}{2}+"
        + given(q, "side")
        + r"\left(2\cdot"
        + given(q, "radius")
        + r"\cdot h+h^2\right)"
    )
    html += line("I=" + latex(q, a.expression) + r"\leq" + latex(q, q.target))
    html += interval_steps(a)
    html += "<p>По методу интервалов получаем промежуток между корнями. По смыслу задачи добавка к радиусу неотрицательна:</p>"
    html += line(
        r"h\in["
        + latex(q, min(a.roots))
        + ";"
        + latex(q, max(a.roots))
        + r"],\quad h\geq0"
    )
    html += line(r"h\in[0;" + latex(q, a.result) + "]")
    return html + final(a, maximum=True)


def bucket(a):
    q = a.question
    length = q.values["length"] / 100
    gravity = q.values["gravity"]
    html = "<p>Переведём длину верёвки в метры. Чтобы вода не выливалась, давление в верхней точке должно быть неотрицательно:</p>"
    html += line(
        "L=" + given(q, "length") + r"\cdot10^{-2}=" + latex(q, length) + r"\ \text{м}"
    )
    html += line(r"P=m\left(\frac{v^2}{L}-g\right)\geq0")
    html += "<p>Масса воды положительна, поэтому на неё можно разделить обе части неравенства:</p>"
    html += line(r"\frac{v^2}{L}-g\geq0")
    html += line(
        r"v^2\geq gL="
        + latex(q, gravity)
        + r"\cdot"
        + latex(q, length)
        + "="
        + latex(q, a.ratio)
    )
    html += "<p>Скорость неотрицательна; берём положительный квадратный корень:</p>"
    html += line(r"v\geq\sqrt{" + latex(q, a.ratio) + "}=" + latex(q, a.result))
    return html + final(a, minimum=True)


def power(a):
    q = a.question
    relation = "=" if q.kind == "stars" else r"\leq"
    coefficient = sp.Poly(a.expression, q.variable).nth(a.power)
    if q.kind == "stars":
        html = "<p>Выразим температуру из закона Стефана–Больцмана и подставим мощность излучения и площадь поверхности звезды:</p>"
        html += line(r"P=\sigma ST^4")
        html += line(r"T^4=\frac{P}{\sigma S}")
        html += line(
            r"T^4=\frac{"
            + given(q, "target")
            + "}{("
            + given(q, "sigma")
            + r")\cdot("
            + given(q, "surface")
            + ")}"
        )
    else:
        html = "<p>Выталкивающая сила не должна превышать заданный предел. Подставим постоянные в формулу:</p>"
        html += line(
            "F_A=" + (r"\alpha\rho gr^3" if q.kind == "sphere" else r"\rho gl^3")
        )
        factors = ([given(q, "alpha")] if q.kind == "sphere" else []) + [
            given(q, "density"),
            given(q, "gravity"),
        ]
        html += line(
            r"\cdot".join("(" + factor + ")" for factor in factors)
            + r"\cdot"
            + q.label
            + "^3"
            + relation
            + latex(q, q.target)
        )
        html += line(
            latex(q, coefficient) + q.label + "^3" + relation + latex(q, q.target)
        )
    html += line(q.label + "^{" + str(a.power) + "}" + relation + latex(q, a.ratio))
    html += "<p>Берём неотрицательный корень. Степенная функция возрастает на неотрицательной полуоси:</p>"
    root = r"\sqrt[" + str(a.power) + "]{" + latex(q, a.ratio) + "}"
    html += line(q.label + relation + root + "=" + latex(q, a.result))
    return html + final(a, maximum=q.kind != "stars")


def proof(a):
    return {
        "thermal": thermal,
        "profit": profit,
        "market": market,
        "bucket": bucket,
        "inertia": inertia,
    }.get(a.question.kind, power)(a)
