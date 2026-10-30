"""Explain polynomial boundaries and the choice of a physical root."""

import sympy as sp

from ..probability.common import line


def latex(value):
    return sp.latex(value)


def measurements(analysis):
    q = analysis.question
    before, after, initial, final = analysis.measurements
    html = "<p>После подъёма воды расстояние до неё уменьшится, поэтому камешек будет падать меньше времени:</p>"
    html += line("t_1=" + latex(before))
    html += line(
        "t_2=" + latex(before) + "-" + latex(q.values["change"]) + "=" + latex(after)
    )
    html += "<p>Найдём расстояние до воды до и после дождя по данному закону:</p>"
    html += line("h(t)=" + latex(q.expression))
    a = sp.Poly(q.expression, q.variable).nth(2)
    html += line(
        "h_1=" + latex(a) + r"\cdot(" + latex(before) + ")^2=" + latex(initial)
    )
    html += line("h_2=" + latex(a) + r"\cdot(" + latex(after) + ")^2=" + latex(final))
    html += "<p>Подъём уровня воды равен уменьшению расстояния:</p>"
    html += line(
        r"\Delta h=h_1-h_2="
        + latex(initial)
        + "-"
        + latex(final)
        + "="
        + latex(analysis.result)
        + r"\ \text{м}"
    )
    return html


def equation_steps(analysis):
    q = analysis.question
    v = latex(q.variable)
    p = (
        sp.Poly(q.expression - q.target, q.variable)
        .clear_denoms(convert=True)[1]
        .primitive()[1]
    )
    if p.LC() < 0:
        p = -p
    a, b, c = (p.nth(i) for i in [2, 1, 0])
    discriminant = b * b - 4 * a * c
    html = "<p>Найдём граничные значения: приравняем заданную величину к требуемому уровню и решим квадратное уравнение:</p>"
    html += line(q.quantity + "(" + v + ")=" + latex(q.target))
    html += line(latex(q.expression) + "=" + latex(q.target))
    html += line(latex(p.as_expr()) + "=0")
    html += line(
        "D=("
        + latex(b)
        + ")^2-4\\cdot("
        + latex(a)
        + r")\cdot("
        + latex(c)
        + ")="
        + latex(discriminant)
    )
    if not analysis.roots:
        html += line(r"D<0\quad\Longrightarrow\quad \text{действительных корней нет}")
    else:
        html += line(
            v
            + r"=\frac{-("
            + latex(b)
            + r")\pm\sqrt{"
            + latex(discriminant)
            + r"}}{2\cdot("
            + latex(a)
            + ")}"
        )
        html += line(
            r";\quad ".join(
                v
                + ("_0" if len(analysis.roots) == 1 else "_{" + str(i) + "}")
                + "="
                + latex(root)
                for i, root in enumerate(analysis.roots, 1)
            )
        )
    return html


def duration(analysis):
    q = analysis.question
    v = latex(q.variable)
    html = "<p>Нужно найти продолжительность промежутка, на котором выполняется условие:</p>"
    html += line(q.quantity + "(" + v + r")\geq" + latex(q.target))
    html += equation_steps(analysis)
    if analysis.interval is None:
        return (
            html
            + "<p>Требуемый уровень не достигается при неотрицательном времени. Продолжительность равна нулю.</p>"
            + line(r"\Delta t=0")
        )
    start, end = analysis.interval
    html += "<p>Ветви параболы направлены вниз. Между граничными моментами значение не меньше требуемого. Учитываем, что время отсчитывается с нуля:</p>"
    html += line(r"t\geq0,\quad t\in[" + latex(start) + ";" + latex(end) + "]")
    html += "<p>Искомая продолжительность равна разности конца и начала промежутка:</p>"
    html += line(
        r"\Delta t="
        + latex(end)
        + "-("
        + latex(start)
        + ")="
        + latex(analysis.result)
        + r"\ \text{"
        + q.unit
        + "}"
    )
    return html


def braking_note(analysis):
    q = analysis.question
    a, b, _ = sp.Poly(q.expression, q.variable).all_coeffs()
    stop = analysis.physical_end
    html = "<p><b>Примечание о выборе корня.</b> Формула пути описывает торможение только от начала движения до полной остановки. При равноускоренном движении:</p>"
    html += line(
        r"x(t)=x_0+v_0t+\frac{a_{\mathrm{зн}}t^2}{2},\quad v(t)=v_0+a_{\mathrm{зн}}t"
    )
    html += line(r"a_{\mathrm{зн}}=" + latex(2 * a) + r"<0,\quad v_0=" + latex(b))
    html += line(
        r"v(t_0)=0\quad\Longrightarrow\quad t_0=-\frac{v_0}{a_{\mathrm{зн}}}="
        + latex(stop)
    )
    html += line(r"0\leq t\leq " + latex(stop))
    if len(analysis.roots) > 1:
        html += "<p>Больший корень за пределами этого промежутка не подходит: если продолжать ту же формулу после остановки, она описывала бы движение назад с увеличением скорости, а не торможение.</p>"
    else:
        html += "<p>Единственный корень соответствует полной остановке автомобиля и допустим по смыслу задачи.</p>"
    return html


def boundary(analysis):
    q = analysis.question
    html = ""
    if q.kind == "tank_fraction":
        html += "<p>В цилиндрическом баке объём воды пропорционален высоте столба. Четверти начального объёма соответствует высота:</p>"
        html += line(
            r"H_{\mathrm{цель}}=\frac{H_0}{4}=\frac{"
            + latex(q.values["initial"])
            + "}{4}="
            + latex(q.target)
        )
    if q.kind == "barrier":
        html += "<p>К высоте стены прибавим требуемый запас высоты:</p>" + line(
            r"y_{\mathrm{цель}}="
            + latex(q.values["wall"])
            + "+"
            + latex(q.values["clearance"])
            + "="
            + latex(q.target)
        )
    if q.kind in ["coverage", "winding", "heater"]:
        html += "<p>До нужного момента должно выполняться ограничение:</p>" + line(
            q.quantity + r"(t)\leq" + latex(q.target)
        )
    html += equation_steps(analysis)
    if q.kind in ["tank_empty", "tank_fraction"]:
        html += "<p>Вода вытекает до первого момента, когда её уровень станет нулевым. Дальнейший рост квадратного многочлена уже не описывает опорожнение бака:</p>"
        html += line(r"0\leq t\leq" + latex(analysis.physical_end))
    elif q.kind == "braking":
        html += braking_note(analysis)
    elif q.kind == "heater":
        html += "<p>Выбираем первый момент достижения предельной температуры. После него прибор перегревается; более позднее охлаждение не позволяет непрерывно оставлять прибор включённым:</p>"
        if len(analysis.roots) == 2:
            html += line(
                r"t\geq0,\quad T(t)\leq"
                + latex(q.target)
                + r"\quad\Longleftrightarrow\quad t\in[0;"
                + latex(analysis.roots[0])
                + r"]\cup["
                + latex(analysis.roots[1])
                + r";+\infty)"
            )
    elif q.kind == "barrier":
        html += "<p>Камень летит над нужным уровнем между найденными границами. Наибольшее допустимое расстояние соответствует правой границе.</p>"
        html += line(
            r"x\in["
            + latex(min(analysis.selected))
            + ";"
            + latex(max(analysis.selected))
            + "]"
        )
    else:
        html += (
            "<p>Искомая величина возрастает с начала движения. Выбираем неотрицательное граничное время; отрицательный корень не имеет физического смысла:</p>"
            + line(r"t\geq0")
        )
    selected = max(analysis.selected) if q.kind == "barrier" else analysis.selected[0]
    html += "<p>Подходящее граничное значение:</p>" + line(
        latex(q.variable) + "=" + latex(selected)
    )
    if q.scale != 1:
        html += "<p>В формуле время задано в часах. Переведём его в минуты:</p>" + line(
            r"t_{\mathrm{мин}}="
            + latex(selected)
            + r"\cdot60="
            + latex(analysis.result)
        )
    else:
        html += line(
            latex(q.variable)
            + "="
            + latex(analysis.result)
            + r"\ \text{"
            + q.unit
            + "}"
        )
    return html


def proof(analysis):
    if analysis.question.kind == "well":
        return measurements(analysis)
    if analysis.question.kind in ["duration", "thermal_duration"]:
        return duration(analysis)
    return boundary(analysis)
