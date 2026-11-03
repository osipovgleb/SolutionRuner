"""Keep the parent's right-triangle angle method and explain the opposite-ray case."""

import hashlib

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..isosceles.angle_proofs import angle, degree
from ..right.altitude_methods import solution_section


def review_parent(html):
    if (
        not isinstance(html, str)
        or hashlib.sha256(html.encode()).hexdigest()
        != "a5d3b824933ea7e66d131f330d61ea170af384cfd5ef666acc24b3bd50b544f0"
    ):
        raise ContentPlanError("the reviewed height/bisector parent method changed")


def render(m):
    hao, aho, aoh, aoc, given = [
        angle(m.name(n)) for n in ["HAO", "AHO", "AOH", "AOC", "BAD"]
    ]
    if m.theta < 45:
        prose = f"<p>Угол {m.name('AOC')} — внешний угол треугольника {m.name('AOH')}, поэтому он равен сумме углов {m.name('HAO')} и {m.name('AHO')}:</p>"
        rows = [
            aoc + "=" + hao + "+" + aho,
            aoc + "=" + degree(m.theta) + r"+90^{\circ}",
            aoc + "=" + degree(m.answer),
        ]
    else:
        prose = f"<p>Угол {m.name('A')} равен удвоенному данному углу и является тупым. Точки H и O лежат по другую сторону от вершины {m.name('A')}, чем {m.name('B')} и D. Лучи {m.name('AH')} и {m.name('AO')} противоположны лучам {m.name('AB')} и {m.name('AD')}, поэтому угол {m.name('HAO')} равен данному. Точка H лежит между O и {m.name('C')}, так что искомый угол совпадает с углом {m.name('AOH')}. Используем сумму углов прямоугольного треугольника {m.name('AOH')}:</p>"
        rows = [
            aoh + r"=180^{\circ}-" + hao + "-" + aho,
            aoh + r"=180^{\circ}-" + degree(m.theta) + r"-90^{\circ}",
            aoh + r"=90^{\circ}-" + degree(m.theta),
            aoh + "=" + degree(m.answer),
            aoc + "=" + aoh + "=" + degree(m.answer),
        ]
    facts = line(hao + "=" + given + "=" + degree(m.theta)) + line(aho + r"=90^{\circ}")
    return solution_section(
        "Решение",
        f"<p>{m.name('AD')} — биссектриса, а {m.name('CH')} — высота. Рассмотрим треугольник {m.name('AOH')}: угол при H прямой.</p>"
        + (facts + prose if m.theta < 45 else prose + facts)
        + "".join(line(row) for row in rows),
    )
