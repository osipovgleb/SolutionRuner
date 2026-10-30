"""Parent-style squaring, exact unit conversions and minimum integer ascent."""

import sympy as sp

from ..calculus.common import answer
from ..probability.common import line

_UNIT_NOTE = "<p>Примечание. Радиус Земли и расстояние до горизонта в этой формуле выражены в километрах, высота — в метрах. За согласование единиц отвечает коэффициент 500. При одинаковых единицах длины формула имеет вид:</p>"


def final(a, minimum=False):
    q = a.question
    unit = {
        r"км/ч^{2}": r"\mathrm{км}/\mathrm{ч}^{2}",
        r"м/с^{2}": r"\mathrm{м}/\mathrm{с}^{2}",
    }.get(q.unit, r"\text{" + q.unit + "}")
    label = q.label + (r"_{\min}" if minimum else "")
    decimal = answer(a.result).replace(",", "{,}")
    return line(
        label
        + "="
        + sp.latex(a.result)
        + ("=" + decimal if a.result.is_Integer is not True else "")
        + r"\ "
        + unit
    )


def motion(a):
    q = a.question
    v = q.values
    relation = r"\geq" if q.relation == "ge" else "="
    html = "<p>Скорость неотрицательна, поэтому обе неотрицательные части можно возвести в квадрат:</p>"
    html += line(r"v=\sqrt{2la}")
    html += line(r"v^2=2la")
    if q.kind == "root_distance":
        native = v["speed"] ** 2 / (2 * v["acceleration"])
        html += line(r"l=\frac{v^2}{2a}")
        html += line(
            r"l=\frac{"
            + sp.latex(v["speed"])
            + r"^2}{2\cdot"
            + sp.latex(v["acceleration"])
            + "}"
        )
        if v["native_unit"] != q.unit:
            html += "<p>По единицам скорости и ускорения путь получен в исходных единицах. Переведём его в единицы ответа:</p>"
            html += line("l=" + sp.latex(native) + r"\ \text{" + v["native_unit"] + "}")
            html += line(
                "l="
                + sp.latex(native)
                + r"\cdot"
                + sp.latex(
                    sp.Rational(1, 1000)
                    if v["native_unit"] == "м"
                    else sp.Integer(1000)
                )
                + r"\ \text{"
                + q.unit
                + "}"
            )
    else:
        html += (
            "<p>Подставим пройденный путь в единицах, согласованных с ускорением:</p>"
        )
        html += line(
            "l="
            + (
                sp.latex(v["path"])
                + r"\cdot"
                + sp.latex(v["native_path"] / v["path"])
                + "="
                if v["path"] != v["native_path"]
                else ""
            )
            + sp.latex(v["native_path"])
            + r"\ \text{"
            + v["native_unit"]
            + "}"
        )
        html += line(
            "2\\cdot"
            + sp.latex(v["native_path"])
            + "a"
            + relation
            + sp.latex(v["speed"])
            + "^2"
        )
        html += line(
            "a"
            + relation
            + r"\frac{"
            + sp.latex(v["speed"] ** 2)
            + r"}{2\cdot"
            + sp.latex(v["native_path"])
            + "}"
        )
        html += "<p>При большем ускорении скорость в конце того же пути будет больше. Граничное значение допускается условием.</p>"
    return html + final(a, q.relation == "ge")


def horizon(a):
    q = a.question
    v = q.values
    km = q.kind == "root_horizon_km"
    coefficient = 2 * v["radius"] if km else v["radius"] / 500
    html = "<p>Дальность и высота неотрицательны. Возведём обе части формулы в квадрат и выразим высоту:</p>"
    html += line(r"l=\sqrt{2Rh}" if km else r"l=\sqrt{\frac{Rh}{500}}")
    html += line("l^2=" + ("2Rh" if km else r"\frac{Rh}{500}"))
    html += line(sp.latex(v["target"]) + "^2=" + sp.latex(coefficient) + "h")
    html += line(sp.latex(coefficient) + "h=" + sp.latex(v["target"] ** 2))
    html += line(
        r"h=\frac{" + sp.latex(v["target"] ** 2) + "}{" + sp.latex(coefficient) + "}"
    )
    html += final(a)
    if km:
        html += "<p>Примечание. Переведём найденную высоту в метры. При наблюдении человеком высоту отсчитывают до уровня глаз:</p>"
        html += line(
            "h="
            + sp.latex(a.result)
            + r"\cdot1000="
            + sp.latex(1000 * a.result)
            + r"\ \text{м}"
        )
    else:
        html += _UNIT_NOTE + line(r"l=\sqrt{2Rh}")
    return html


def steps(a):
    q = a.question
    v = q.values
    initial = v["initial_height"]
    needed = 500 * v["target"] ** 2 / v["radius"]
    rise = max(needed - initial, 0)
    html = "<p>По формуле дальности горизонта найдём исходную и требуемую высоту. Обе части неотрицательны:</p>"
    html += line(r"l=\sqrt{\frac{Rh}{500}}\quad\Longrightarrow\quad h=\frac{500l^2}{R}")
    html += line(
        r"h_0=\frac{500\cdot"
        + sp.latex(v["before"])
        + "^2}{"
        + sp.latex(v["radius"])
        + "}="
        + sp.latex(initial)
    )
    html += line(
        r"h_1=\frac{500\cdot"
        + sp.latex(v["target"])
        + "^2}{"
        + sp.latex(v["radius"])
        + "}="
        + sp.latex(needed)
    )
    html += "<p>Если требуемая дальность уже достигнута, подниматься не нужно. Иначе найдём необходимый подъём и переведём высоту ступеньки в метры:</p>"
    html += line(r"\Delta h=\max(h_1-h_0,0)=" + sp.latex(rise))
    html += line(
        "s="
        + sp.latex(v["step"])
        + r"\cdot10^{-2}="
        + sp.latex(v["step_m"])
        + r"\ \text{м}"
    )
    html += line(r"n\geq\frac{\Delta h}{s}=" + sp.latex(rise / v["step_m"]))
    html += "<p>Количество ступенек целое, поэтому берём наименьшее целое, удовлетворяющее неравенству.</p>"
    html += final(a, True)
    if a.result > 0:
        html += line(
            sp.latex(initial + (a.result - 1) * v["step_m"])
            + "<"
            + sp.latex(needed)
            + r"\leq"
            + sp.latex(initial + a.result * v["step_m"])
        )
    return html + _UNIT_NOTE + line(r"l=\sqrt{2Rh}")


def rocket(a):
    q = a.question
    v = q.values
    html = "<p>По смыслу задачи скорость неотрицательна и меньше скорости света:</p>"
    html += line(r"0\leq v<c=" + sp.latex(v["light"]))
    if v["target"] >= v["length"]:
        html += "<p>Исходная длина уже не превышает заданного предела, поэтому допустима нулевая скорость.</p>"
        html += line(sp.latex(v["length"]) + r"\leq" + sp.latex(v["target"]))
        return html + final(a, True)
    ratio = v["light"] ** 2 * (1 - (v["target"] / v["length"]) ** 2)
    html += "<p>Найдём скорость, при которой длина равна заданному пределу. Разделим на положительную исходную длину и возведём неотрицательные части в квадрат:</p>"
    html += line(r"l_0\sqrt{1-\frac{v^2}{c^2}}=" + sp.latex(v["target"]))
    html += line(
        sp.latex(v["length"])
        + r"\sqrt{1-\frac{v^2}{("
        + sp.latex(v["light"])
        + ")^2}}="
        + sp.latex(v["target"])
    )
    html += line(
        r"1-\frac{v^2}{"
        + sp.latex(v["light"] ** 2)
        + "}="
        + sp.latex((v["target"] / v["length"]) ** 2)
    )
    html += line(r"v^2=c^2\left(1-\frac{l^2}{l_0^2}\right)=" + sp.latex(ratio))
    html += line(r"v=\sqrt{" + sp.latex(ratio) + "}=" + sp.latex(a.result))
    html += "<p>С увеличением допустимой скорости наблюдаемая длина уменьшается, поэтому найденная граница даёт минимальную скорость.</p>"
    return html + final(a, True)


def rise(a):
    v = a.question.values
    initial = v["initial_height"]
    needed = 500 * v["target"] ** 2 / v["radius"]
    html = "<p>Найдём высоту для каждого из двух расстояний до горизонта. Обе части формулы неотрицательны, поэтому можно возвести их в квадрат:</p>"
    html += line(r"l=\sqrt{\frac{Rh}{500}}\quad\Longrightarrow\quad h=\frac{500l^2}{R}")
    for label, distance, height in [
        ("h_0", v["before"], initial),
        ("h_1", v["target"], needed),
    ]:
        html += line(
            label
            + r"=\frac{500\cdot("
            + sp.latex(distance)
            + ")^2}{"
            + sp.latex(v["radius"])
            + "}="
            + sp.latex(height)
            + r"\ \text{м}"
        )
    html += "<p>Чтобы видеть горизонт дальше, нужно подняться на разность найденных высот:</p>"
    html += line(r"\Delta h=h_1-h_0=" + sp.latex(needed) + "-" + sp.latex(initial))
    html += final(a)
    html += _UNIT_NOTE.replace("Примечание.", "Примечание Дмитрия Гущина.") + line(
        r"l=\sqrt{2Rh}"
    )
    html += "<p>В инженерных расчётах выбирают удобные единицы. Например, сопротивление проводника находят по формуле:</p>"
    html += line(r"R=\rho\frac{l}{S}")
    html += "<p>Если удельное сопротивление выражено в Ом·мм²/м, длину подставляют в метрах, а сечение — в квадратных миллиметрах, и получают сопротивление в омах. Ниже приведён отдельный пример из школьного курса физики; его данные не относятся к задаче о горизонте.</p>"
    return html


PROOFS = {
    "root_acceleration": motion,
    "root_acceleration_min": motion,
    "root_distance": motion,
    "root_horizon": horizon,
    "root_horizon_km": horizon,
    "root_steps": steps,
    "rocket": rocket,
    "root_rise": rise,
}
