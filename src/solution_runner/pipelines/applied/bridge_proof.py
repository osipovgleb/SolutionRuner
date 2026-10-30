"""Bridge substitution and all three parent notes, with a recomputed minimum."""

import sympy as sp

from ..probability.common import line


def catenary_note():
    html = "<p><b>Примечание 1.</b></p><p>Линия, по которой провисает тяжелая цепь в поле силы тяжести, является «цепной линией», которая похожа на параболу, но отличается от неё. Уравнение цепной линии:</p>"
    html += line(r"y=\frac{a}{2}(e^{x\div a}+e^{-x\div a})")
    html += "<p>Здесь <i>a</i> — параметр, зависящий от материала. Ненагруженная цепь, подвешенная между двумя опорами, принимает форму цепной линии. Если весом цепи можно пренебречь, а вес моста равномерно распределён вдоль его длины, цепь принимает форму параболы. Если же вес цепи сравним с весом полотна (скажем, для небольших легких пешеходных мостов в горах), то его форма будет промежуточной между цепной линией и параболой.</p>"
    return html


def minimum_note(a):
    q = a.question
    quadratic, linear, _ = sp.Poly(q.expression, q.variable).all_coeffs()
    vertex, minimum = a.measurements
    html = "<p><b>Примечание 2.</b></p><p>Проверим координаты нижней точки параболы, заданной условием:</p>"
    html += line(
        r"x_{\min}=-\frac{"
        + sp.latex(linear)
        + "}{2\\cdot("
        + sp.latex(quadratic)
        + ")}="
        + sp.latex(vertex)
    )
    html += line(
        r"y_{\min}=y\left("
        + sp.latex(vertex)
        + r"\right)="
        + sp.latex(minimum)
        + r"\,\mathrm{м}"
    )
    if minimum < 0:
        return (
            html
            + "<p>Ордината нижней точки отрицательна. По этой формуле цепь в центре оказывается ниже полотна, поэтому подвески там не могут удерживать полотно. Это недостаток модели из условия; длину выбранной подвески вычисляем по заданному уравнению.</p>"
        )
    if minimum == 0:
        return (
            html
            + "<p>В нижней точке цепь касается уровня полотна: ордината равна нулю.</p>"
        )
    return (
        html
        + "<p>Ордината нижней точки положительна, поэтому на всём пролёте между пилонами цепь расположена выше полотна.</p>"
    )


def terminology_note():
    return "<p><b>Примечание 3.</b></p><p>В решении и примечаниях выше мы использовали терминологию из условия. Она не является общепринятой. В учебной и профессиональной литературе то, что в условии названо цепью, называется нитью, поддерживающие полотно тросы называются подвеской, а вант на представленном в условии мосту нет (и сам мост — не вантовый!). Дело в том, что несущий элемент вантового моста — прямолинейные ванты, прикрепленные к пилонам. Вантовые мосты бывают двух типов — «веерный» и «арфовый», на рисунке ниже они изображены слева и справа соответственно.</p>"


def proof(a):
    q = a.question
    distance = q.values["distance"]
    quadratic, linear, constant = sp.Poly(q.expression, q.variable).all_coeffs()
    label = "y(" + sp.latex(distance) + ")"
    html = "<p>Найдём длину ванты на указанном расстоянии от левого пилона. В силу симметрии параболы она равна длине ванты на таком же расстоянии от правого пилона. Задача сводится к вычислению значения y в этой точке:</p>"
    html += line("x=" + sp.latex(distance) + r"\,\mathrm{м}")
    html += line("y(x)=" + sp.latex(q.expression))
    terms = [quadratic * distance**2, linear * distance, constant]
    html += line(
        label
        + "=("
        + sp.latex(quadratic)
        + r")\cdot("
        + sp.latex(distance)
        + ")^2+("
        + sp.latex(linear)
        + r")\cdot("
        + sp.latex(distance)
        + ")+"
        + sp.latex(constant)
    )
    html += line(label + "=" + "+".join("(" + sp.latex(term) + ")" for term in terms))
    html += line(label + "=" + sp.latex(a.result) + r"\,\mathrm{м}")
    return html + catenary_note() + minimum_note(a) + terminology_note()
