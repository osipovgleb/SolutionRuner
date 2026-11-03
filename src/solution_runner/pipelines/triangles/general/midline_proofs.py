"""Preserve similarity, both inverse cases, and the trapezoid subtraction."""

import hashlib

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..isosceles.side_altitude_proofs import number
from ..right.altitude_methods import solution_section

PARENTS = {
    "general-triangle-27592-midline-area": "a0400ecf884041708ff6f7a7a7a6e767336f076c515996fc038839b8cf9594f9",
    "general-triangle-317337-midline-small-area-to-total": "afea1676efa4cfb0ea1ddd92979e6cb8234d02e8617f068364da4696bbd495ff",
    "general-triangle-319058-midline-trapezoid-area": "11008c32b34ae38faa67fa4b93c125f6af4a7878668cd8782ce9553bb4077e89",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != PARENTS.get(rule):
        raise ContentPlanError("the complete midline parent method must be reviewed")


def _area(m, name):
    return "S_{" + ("ABC" if name == "ABC" else m.name(name)) + "}"


def _small(m):
    small, total = _area(m, "CDE"), _area(m, "ABC")
    return (
        f"<p>Средняя линия {m.name('DE')} отсекает от треугольника ABC подобный ему треугольник {m.name('CDE')} с коэффициентом подобия 1/2:</p>"
        + line(r"k=\frac{1}{2}")
        + "<p>Площади подобных фигур относятся как квадрат коэффициента подобия:</p>"
        + line(small + r"=k^{2}" + total)
        + line(small + r"=\left(\frac{1}{2}\right)^{2}" + total)
        + line(small + r"=\frac{1}{4}\cdot " + number(m.total))
        + line(small + r"=\frac{" + number(m.total) + "}{4}")
        + line(small + "=" + number(m.small))
    )


def _total(m, image):
    small, total = _area(m, "CDE"), _area(m, "ABC")
    return (
        "<p>Рассмотрим два случая.</p>"
        + f"<p>1. Средняя линия DE параллельна стороне {m.name('AB')}. Треугольник ABC подобен треугольнику {m.name('DEC')} с коэффициентом 2. Площади подобных фигур относятся как квадрат коэффициента подобия:</p>"
        + line(total + r"=2^{2}" + small)
        + line(total + r"=4\cdot " + number(m.small))
        + line(total + "=" + number(m.total))
        + f"<p>2. Средняя линия DE не параллельна стороне {m.name('AB')}. Пусть для определенности точка D — середина стороны {m.name('AC')}. Тогда DE — медиана треугольника {m.name('ACE')}, поэтому площади треугольников {m.name('CDE')} и {m.name('ADE')} равны:</p>"
        + image
        + line(small + "=" + _area(m, "ADE"))
        + f"<p>Отрезок {m.name('CE')} — медиана треугольника ABC. Поэтому площади треугольников {m.name('AEC')} и {m.name('CBE')} равны:</p>"
        + line(_area(m, "AEC") + "=" + _area(m, "CBE") + "=2" + small)
        + line(total + "=" + _area(m, "AEC") + "+" + _area(m, "CBE"))
        + line(total + "=" + small + "+" + _area(m, "ADE") + "+" + _area(m, "CBE"))
        + line(total + "=4" + small)
        + line(total + r"=4\cdot " + number(m.small) + "=" + number(m.total))
    )


def _trapezoid(m):
    small, total = _area(m, "CDE"), _area(m, "ABC")
    trapezoid = "S_{" + m.name("ABED") + "}"
    return (
        f"<p>Треугольник {m.name('CDE')} подобен треугольнику {m.name('CAB')} с коэффициентом 0,5. Площади подобных фигур относятся как квадрат коэффициента подобия:</p>"
        + line(small + r"=\left(\frac{1}{2}\right)^{2}" + total)
        + line(small + r"=\frac{1}{4}\cdot " + number(m.total))
        + line(small + "=" + number(m.small))
        + "<p>Площадь трапеции равна разности площадей большого и малого треугольников:</p>"
        + line(trapezoid + "=" + total + "-" + small)
        + line(trapezoid + "=" + number(m.total) + "-" + number(m.small))
        + line(trapezoid + "=" + number(m.answer))
    )


def render(m, image=""):
    body = (
        _total(m, image)
        if m.mode == "total"
        else _small(m)
        if m.mode == "small"
        else _trapezoid(m)
    )
    return solution_section("Решение", body)
