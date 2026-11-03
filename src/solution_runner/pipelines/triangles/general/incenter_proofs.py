"""Preserve the parent half-angle substitution and the three-triangle method."""

import hashlib

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..isosceles.angle_proofs import angle, degree
from ..right.altitude_methods import solution_section

PARENTS = {
    "general-triangle-27764-incenter-angle": "441ed0648c0522a250505e3c993f45eb73063ad725ccf9400fabdc3b155ddd09",
    "general-triangle-27778-incenter-bisectors-angle": "f4099294aec748d7cc037802a748f313dffd0d37d933d0c0bc4913362c19aeaf",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != PARENTS.get(rule):
        raise ContentPlanError("the complete incenter parent method must be reviewed")


def _between(m):
    a, b, c = (angle(m.name(n)) for n in "ABC")
    left, right, target = (angle(m.name(n)) for n in ("OAB", "OBA", "AOB"))
    return (
        f"<p>Рассмотрим угол {m.name('AOB')} в треугольнике {m.name('AOB')}. По сумме углов треугольника и свойству биссектрис:</p>"
        + line(target + r"=180^{\circ}-(" + left + "+" + right + ")")
        + line(left + "+" + right + r"=\frac{1}{2}(" + a + "+" + b + ")")
        + line(target + r"=180^{\circ}-\frac{1}{2}(" + a + "+" + b + ")")
        + "<p>Сумма углов исходного треугольника равна 180°. Подставим выражение для двух оставшихся углов и выполним вычисления:</p>"
        + line(a + "+" + b + r"=180^{\circ}-" + c)
        + line(target + r"=180^{\circ}-\frac{1}{2}(180^{\circ}-" + c + ")")
        + line(target + r"=180^{\circ}-\frac{1}{2}(180^{\circ}-" + degree(m.c) + ")")
        + line(target + r"=180^{\circ}-\frac{1}{2}\cdot " + degree(180 - m.c))
        + line(target + r"=180^{\circ}-" + degree((180 - m.c) / 2))
        + line(target + "=" + degree(m.answer))
    )


def _foot(m):
    a, b, c = (angle(m.name(n)) for n in "ABC")
    f, target = angle("F"), angle(m.name("AOF"))
    return (
        "<p>В треугольнике ABC найдем третий угол по сумме углов:</p>"
        + line(c + r"=180^{\circ}-" + a + "-" + b)
        + line(c + r"=180^{\circ}-" + degree(m.values[0]) + "-" + degree(m.values[1]))
        + line(c + "=" + degree(m.c))
        + f"<p>В треугольнике {m.name('ACF')} луч {m.name('CF')} делит угол {m.name('C')} пополам. Найдем угол F этого треугольника:</p>"
        + line(f + r"=180^{\circ}-" + a + "-" + angle(m.name("ACF")))
        + line(
            f
            + r"=180^{\circ}-"
            + degree(m.values[0])
            + r"-\frac{"
            + degree(m.c)
            + "}{2}"
        )
        + line(f + "=" + degree(m.f))
        + f"<p>В треугольнике {m.name('AOF')} луч {m.name('AO')} лежит на биссектрисе угла {m.name('A')}. По сумме углов получим:</p>"
        + line(target + r"=180^{\circ}-" + angle(m.name("OAF")) + "-" + f)
        + line(
            target
            + r"=180^{\circ}-\frac{"
            + degree(m.values[0])
            + "}{2}-"
            + degree(m.f)
        )
        + line(target + "=" + degree(m.answer))
    )


def render(m):
    return solution_section("Решение", _between(m) if m.mode == "between" else _foot(m))
