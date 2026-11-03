"""Keep each equal-side parent's angle method, with explicit numerical steps."""

import hashlib

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..isosceles.angle_proofs import angle, degree
from ..right.altitude_methods import solution_section

PARENTS = {
    "general-triangle-27769-extension-isosceles-angle": "4ce83d90824297e088fe7a5716550f7b890f0dd7f6250a0c961cb66b1a384a8e",
    "general-triangle-27776-bisector-congruent-angle": "04317116ca7b2d2aef49735495a9d13868072772761de6ea75258a7f5141e3fe",
    "general-triangle-27777-exterior-bisector-isosceles-angle": "9e2b21ac2516cc26b64af649e1e2717cecb057391712981dcccf84465194bdfb",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != PARENTS.get(rule):
        raise ContentPlanError("the complete equal-side parent method must be reviewed")


def _extension(m):
    a, b, c, cbd, d = [angle(m.name(n)) for n in ["A", "B", "C", "CBD", "D"]]
    adjacent = 180 - m.beta
    return (
        f"<p>Сумма углов треугольника {m.name('ABC')} равна 180°, поэтому:</p>"
        + line(b + r"=180^{\circ}-" + a + "-" + c)
        + line(b + r"=180^{\circ}-" + degree(m.alpha) + "-" + degree(m.gamma))
        + line(b + "=" + degree(m.beta))
        + f"<p>Угол {m.name('CBD')} смежный с углом {m.name('B')}, поэтому:</p>"
        + line(cbd + r"=180^{\circ}-" + b)
        + line(cbd + r"=180^{\circ}-" + degree(m.beta))
        + line(cbd + "=" + degree(adjacent))
        + f"<p>Треугольник {m.name('CBD')} — равнобедренный, так как {m.name('BD')} = {m.name('BC')}. Углы при основании равны. Следовательно:</p>"
        + line(d + r"=\frac{180^{\circ}-" + cbd + "}{2}")
        + line(d + r"=\frac{180^{\circ}-" + degree(adjacent) + "}{2}")
        + line(d + "=" + degree(m.answer))
    )


def _congruent(m):
    b, c, dea, deb, bde = [angle(m.name(n)) for n in ["B", "C", "DEA", "DEB", "BDE"]]
    adjacent = 180 - m.gamma
    return (
        f"<p>Треугольники {m.name('CAD')} и {m.name('EAD')} равны по двум сторонам и углу между ними: {m.name('AD')} — общая сторона, {m.name('AE')} = {m.name('AC')}, а углы при {m.name('A')} равны, поскольку {m.name('AD')} — биссектриса. Поэтому:</p>"
        + line(c + "=" + dea + "=" + degree(m.gamma))
        + f"<p>Углы {m.name('DEA')} и {m.name('DEB')} смежные, поэтому:</p>"
        + line(deb + r"=180^{\circ}-" + dea)
        + line(deb + r"=180^{\circ}-" + degree(m.gamma))
        + line(deb + "=" + degree(adjacent))
        + f"<p>Сумма углов треугольника {m.name('BDE')} равна 180°. Следовательно:</p>"
        + line(bde + r"=180^{\circ}-" + b + "-" + deb)
        + line(bde + r"=180^{\circ}-" + degree(m.beta) + "-" + degree(adjacent))
        + line(bde + "=" + degree(m.answer))
    )


def _exterior(m):
    a, b, bdc, bcd, cbd, bde = [
        angle(m.name(n)) for n in ["A", "B", "BDC", "BCD", "CBD", "BDE"]
    ]
    forward = m.beta > m.alpha
    half = (m.alpha + m.beta) / 2
    phi = half if forward else 180 - half
    adjacent = 180 - m.beta if forward else m.beta
    numerator = a + "+" + b
    numeric = degree(m.alpha) + "+" + degree(m.beta)
    formula = r"\frac{" + numerator + "}{2}"
    substitution = r"\frac{" + numeric + "}{2}"
    if not forward:
        formula, substitution = (
            r"180^{\circ}-" + formula,
            r"180^{\circ}-" + substitution,
        )
    location = (
        f"Точка D лежит на продолжении {m.name('AB')} за {m.name('B')}."
        if forward
        else f"Точка D лежит на продолжении {m.name('BA')} за {m.name('A')}. Луч {m.name('CD')} противоположен биссектрисе угла {m.name('BCE')}."
    )
    cbd_relation = r"180^{\circ}-" + b if forward else b
    cbd_substitution = r"180^{\circ}-" + degree(m.beta) if forward else degree(m.beta)
    return (
        f"<p>Треугольники {m.name('CBD')} и {m.name('ECD')} равны по двум сторонам и углу между ними: {m.name('CB')} = {m.name('CE')}, {m.name('CD')} — общая сторона, а углы при {m.name('C')} равны благодаря внешней биссектрисе. Поэтому углы {m.name('BDC')} и {m.name('CDE')} равны. {location} Следовательно:</p>"
        + line(bde + "=2" + bdc)
        + f"<p>Внешний угол {m.name('BCE')} равен сумме углов {m.name('A')} и {m.name('B')}. Учитывая положение луча {m.name('CD')}, найдём два угла треугольника {m.name('BCD')}:</p>"
        + line(bcd + "=" + formula)
        + line(bcd + "=" + substitution)
        + line(bcd + "=" + degree(phi))
        + line(cbd + "=" + cbd_relation)
        + line(cbd + "=" + cbd_substitution)
        + (line(cbd + "=" + degree(adjacent)) if forward else "")
        + f"<p>Угол {m.name('BDC')} дополняет сумму двух других углов треугольника {m.name('BCD')} до 180°. Подставим найденные углы и удвоим результат:</p>"
        + line(bde + r"=2(180^{\circ}-" + degree(phi) + "-" + degree(adjacent) + ")")
        + line(bde + r"=2\cdot" + degree(m.answer / 2) + "=" + degree(m.answer))
    )


def render(model):
    method = {"extension": _extension, "congruent": _congruent, "exterior": _exterior}[
        model.mode
    ]
    return solution_section("Решение", method(model))
