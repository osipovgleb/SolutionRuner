"""Parent methods: concentration, conserved dry matter and explicit substitution."""

import sympy as sp

from ..probability.common import line
from .math_common import number, primitive

M1, M2, C1, C2, X = sp.symbols("m_1 m_2 c_1 c_2 x", real=True)


def system(rows):
    return line(r"\begin{cases}" + r"\\".join(rows) + r"\end{cases}")


def volume_note(q):
    if q.unit != "л" and q.kind != "dilution":
        return ""
    html = "<p><b>Примечание.</b> В текстовых задачах по математике предполагается, что объем раствора, образованного при сливании двух жидкостей, равен сумме их объемов. Это такая же условность, как «мгновенный разворот» в задачах на движение. В действительности объем (в отличие от массы) не всегда обладает таким свойством.</p>"
    if q.unit == "кг":
        html += "<p>В этой задаче заданы массы раствора и воды; массы складываются непосредственно.</p>"
    return html


def dilution(a):
    q = a.question
    first, added = a.amounts
    pure = first * a.fractions[0]
    symbol = "V" if q.unit == "л" else "m"
    html = "<p>Концентрация равна доле растворённого вещества. При добавлении воды количество этого вещества остаётся прежним:</p>"
    html += line(
        r"C=\frac{"
        + symbol
        + r"_{\mathrm{в-ва}}}{"
        + symbol
        + r"_{\mathrm{р-ра}}}\cdot100\%"
    )
    html += line(
        symbol
        + r"_{\mathrm{в-ва}}="
        + number(a.fractions[0])
        + r"\cdot"
        + number(first)
        + "="
        + number(pure)
    )
    html += "<p>Общее количество раствора увеличится на количество добавленной воды. Найдём новую концентрацию:</p>"
    html += line(
        symbol
        + r"_{\mathrm{р-ра}}="
        + number(first)
        + "+"
        + number(added)
        + "="
        + number(first + added)
    )
    html += line(
        r"C=\frac{" + number(pure) + "}{" + number(first + added) + r"}\cdot100\%"
    )
    return html + line("C=" + number(a.result) + r"\%") + volume_note(q)


def equal(a):
    v = a.question.values
    c1, c2 = a.fractions
    html = "<p>Процентная концентрация — массовая доля растворённого вещества. Пусть масса каждого исходного раствора равна m, где m&gt;0. Тогда масса смеси равна 2m:</p>"
    html += line(r"\omega=\frac{m_{\mathrm{в-ва}}}{m_{\mathrm{р-ра}}}\cdot100\%")
    html += line(
        "c_1="
        + number(v["p1"])
        + "/100="
        + number(c1)
        + r",\quad c_2="
        + number(v["p2"])
        + "/100="
        + number(c2)
    )
    html += line(
        r"\omega=\frac{" + number(c1) + "m+" + number(c2) + r"m}{2m}\cdot100\%"
    )
    html += "<p>Количество вещества складывается, а одинаковые положительные массы сокращаются:</p>"
    html += line(r"\omega=\frac{" + number(c1 + c2) + r"}{2}\cdot100\%")
    return html + line(r"\omega=" + number(a.result) + r"\%")


def weighted(a):
    q = a.question
    first, second = a.amounts
    pure1, pure2 = first * a.fractions[0], second * a.fractions[1]
    symbol = "V" if q.unit == "л" else "m"
    html = "<p>Найдём количество растворённого вещества в каждой порции. При смешивании эти количества складываются:</p>"
    html += line(
        r"C=\frac{"
        + symbol
        + r"_{\mathrm{в-ва}}}{"
        + symbol
        + r"_{\mathrm{р-ра}}}\cdot100\%"
    )
    html += line(
        symbol
        + "_1="
        + number(a.fractions[0])
        + r"\cdot"
        + number(first)
        + "="
        + number(pure1)
    )
    html += line(
        symbol
        + "_2="
        + number(a.fractions[1])
        + r"\cdot"
        + number(second)
        + "="
        + number(pure2)
    )
    html += "<p>Разделим общее количество вещества на общее количество раствора:</p>"
    html += line(
        symbol
        + r"_{\mathrm{р-ра}}="
        + number(first)
        + "+"
        + number(second)
        + "="
        + number(first + second)
    )
    html += line(
        r"C=\frac{"
        + number(pure1)
        + "+"
        + number(pure2)
        + "}{"
        + number(first + second)
        + r"}\cdot100\%"
    )
    return html + line("C=" + number(a.result) + r"\%") + volume_note(q)


def drying(a):
    v = a.question.values
    before, after = a.fractions
    pure = v["final_mass"] * after
    html = "<p>При сушке испаряется вода, а масса сухого вещества сохраняется. Найдём доли сухого вещества в винограде и изюме:</p>"
    html += line("c_1=1-" + number(v["grape_water"]) + "/100=" + number(before))
    html += line("c_2=1-" + number(v["raisin_water"]) + "/100=" + number(after))
    html += line(
        r"m_{\mathrm{сух}}="
        + number(v["final_mass"])
        + r"\cdot"
        + number(after)
        + "="
        + number(pure)
        + r"\,\mathrm{кг}"
    )
    html += "<p>Та же масса сухого вещества должна содержаться в исходном винограде. Выразим его массу:</p>"
    html += line("m" + r"\cdot" + number(before) + "=" + number(pure))
    return html + line(
        r"m=\frac{"
        + number(pure)
        + "}{"
        + number(before)
        + "}="
        + number(a.result)
        + r"\,\mathrm{кг}"
    )


def linear_steps(a, variables, eliminate):
    equations = [primitive(e, variables) for e in a.equations]
    var, other = variables[eliminate], variables[1 - eliminate]
    pivot = next(i for i, e in enumerate(equations) if e.coeff(var) != 0)
    expressed = sp.expand(-equations[pivot].subs(var, 0) / equations[pivot].coeff(var))
    rest = equations[1 - pivot]
    html = "<p>Решим систему подстановкой. Сначала приведём уравнения к целым коэффициентам и выразим одну неизвестную:</p>"
    html += system([sp.latex(e) + "=0" for e in equations])
    html += line(sp.latex(var) + "=" + sp.latex(expressed))
    html += line(
        "("
        + number(rest.coeff(var))
        + r")\cdot\left("
        + sp.latex(expressed)
        + r"\right)+("
        + number(rest.coeff(other))
        + r")\cdot"
        + sp.latex(other)
        + "+("
        + number(rest.subs({var: 0, other: 0}))
        + ")=0"
    )
    html += line(sp.latex(primitive(rest.subs(var, expressed), (other,))) + "=0")
    values = a.fractions if a.question.kind == "unknown_concentrations" else a.amounts
    return html + system(
        [
            sp.latex(variable) + "=" + number(value)
            for variable, value in zip(variables, values, strict=True)
        ]
    )


def alloy_total(a):
    v = a.question.values
    c1, c2 = a.fractions
    html = "<p>Пусть массы первого и второго сплавов равны m₁ и m₂ кг. Запишем общий вес и сохранение массы никеля:</p>"
    html += system(
        [
            "m_1+m_2=" + number(v["total"]),
            number(c1)
            + "m_1+"
            + number(c2)
            + "m_2="
            + number(v["target"] / 100)
            + r"\cdot"
            + number(v["total"]),
        ]
    )
    html += linear_steps(a, (M1, M2), 1)
    html += "<p>Первый сплав легче второго. Найдём разность масс:</p>"
    return html + line(
        "m_2-m_1="
        + number(a.amounts[1])
        + "-"
        + number(a.amounts[0])
        + "="
        + number(a.result)
        + r"\,\mathrm{кг}"
    )


def alloy_difference(a):
    v = a.question.values
    c1, c2 = a.fractions
    m = sp.Symbol("m", real=True)
    d, target = v["difference"], v["target"] / 100
    html = "<p>Пусть масса первого сплава равна m кг. Тогда второй сплав имеет массу m+d, а смесь — 2m+d. Подставим заданную разность масс:</p>"
    html += line("m_2=m+" + number(d) + r",\quad m_3=2m+" + number(d))
    html += "<p>Масса меди сохраняется. Составим и решим линейное уравнение:</p>"
    html += line(
        number(c1)
        + "m+"
        + number(c2)
        + "(m+"
        + number(d)
        + ")="
        + number(target)
        + "(2m+"
        + number(d)
        + ")"
    )
    html += line(
        sp.latex(primitive(c1 * m + c2 * (m + d) - target * (2 * m + d), (m,))) + "=0"
    )
    html += line("m=" + number(a.amounts[0]))
    html += "<p>Теперь найдём массу третьего сплава:</p>"
    return html + line(
        r"m_3=2\cdot"
        + number(a.amounts[0])
        + "+"
        + number(d)
        + "="
        + number(a.result)
        + r"\,\mathrm{кг}"
    )


def two_scenarios(a):
    v = a.question.values
    c1, c2 = a.fractions
    base = number(c1) + "m_1+" + number(c2) + "m_2"
    html = "<p>Пусть массы исходных растворов равны m₁ и m₂ кг. В первом случае добавляем чистую воду, во втором — раствор кислоты. Для каждого случая запишем сохранение массы кислоты:</p>"
    html += system(
        [
            base
            + "="
            + number(v["target"] / 100)
            + "(m_1+m_2+"
            + number(v["water"])
            + ")",
            base
            + "+"
            + number(v["alternative"] / 100)
            + r"\cdot"
            + number(v["added"])
            + "="
            + number(v["second_target"] / 100)
            + "(m_1+m_2+"
            + number(v["added"])
            + ")",
        ]
    )
    html += linear_steps(a, (M1, M2), 0)
    return html + line("m_1=" + number(a.result) + r"\,\mathrm{кг}")


def unknown_concentrations(a):
    v = a.question.values
    first, second = a.amounts
    html = "<p>Пусть доли кислоты в исходных растворах равны c₁ и c₂. При смешивании равных масс концентрация равна их среднему арифметическому. При смешивании всех растворов складываются массы кислоты:</p>"
    html += system(
        [
            "c_1+c_2=" + number(2 * v["mean"] / 100),
            number(first)
            + "c_1+"
            + number(second)
            + "c_2="
            + number(first + second)
            + r"\cdot"
            + number(v["target"] / 100),
        ]
    )
    html += linear_steps(a, (C1, C2), 1)
    html += "<p>Умножим концентрацию первого раствора на его массу:</p>"
    return html + line(
        "m_1="
        + number(a.fractions[0])
        + r"\cdot"
        + number(first)
        + "="
        + number(a.result)
        + r"\,\mathrm{кг}"
    )


def ratio(a):
    v = a.question.values
    scale = 2 * v["target"] / (v["r1"] + v["r2"])
    html = "<p>Обозначим концентрации растворов в процентах через r₁x и r₂x, где коэффициенты заданы отношением. Пусть масса каждого раствора равна m&gt;0:</p>"
    html += line("C_1=" + number(v["r1"]) + "x,\\quad C_2=" + number(v["r2"]) + "x")
    html += line(
        r"\frac{"
        + number(v["r1"])
        + r"x}{100}m+\frac{"
        + number(v["r2"])
        + r"x}{100}m=\frac{"
        + number(v["target"])
        + r"}{100}\cdot2m"
    )
    html += "<p>Сократим положительную массу и найдём x, затем вычтем первую концентрацию из второй:</p>"
    html += line(
        "("
        + number(v["r1"])
        + "+"
        + number(v["r2"])
        + ")x=2\\cdot"
        + number(v["target"])
    )
    html += line("x=" + number(scale))
    return html + line(
        "C_2-C_1=("
        + number(v["r2"])
        + "-"
        + number(v["r1"])
        + ")"
        + r"\cdot"
        + number(scale)
        + "="
        + number(a.result)
        + r"\%"
    )


def acid_difference(a):
    v = a.question.values
    d, chosen = v["difference"] / 100, a.fractions[0]
    html = "<p>Масса раствора равна массе кислоты, делённой на её долю. Пусть концентрация первого раствора равна x, тогда концентрация второго равна x−d. Разность процентов переводим в разность долей:</p>"
    html += line(
        r"m_{\mathrm{р-ра}}=\frac{m_{\mathrm{к-ты}}}{c},\quad d="
        + number(v["difference"])
        + "/100="
        + number(d)
        + r",\quad "
        + number(d)
        + r"<x\leq1"
    )
    html += line(
        r"\frac{"
        + number(v["acid1"])
        + r"}{x}+\frac{"
        + number(v["acid2"])
        + "}{x-"
        + number(d)
        + "}="
        + number(v["total"])
    )
    html += "<p>На допустимом промежутке знаменатели положительны. Умножим уравнение на их произведение и разложим полученный многочлен на множители:</p>"
    p = primitive(a.equations[0], (X,))
    html += line(sp.latex(p) + "=0")
    html += line(sp.latex(sp.factor(p)) + "=0")
    html += line(
        r"x\in\left\{" + ";".join(number(root) for root in a.roots) + r"\right\}"
    )
    html += "<p>Выберем корень, при котором обе концентрации допустимы, и выразим искомую концентрацию в процентах:</p>"
    html += line("x=" + number(chosen))
    return html + line(
        "C_1=" + number(chosen) + r"\cdot100\%=" + number(a.result) + r"\%"
    )


_PROOFS = {
    "dilution": dilution,
    "equal": equal,
    "weighted": weighted,
    "drying": drying,
    "alloy_total": alloy_total,
    "alloy_difference": alloy_difference,
    "two_scenarios": two_scenarios,
    "unknown_concentrations": unknown_concentrations,
    "ratio": ratio,
    "acid_difference": acid_difference,
}


def proof(a):
    return _PROOFS[a.question.kind](a)
