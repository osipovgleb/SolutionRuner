"""The five parent methods for the long diagonal of a sixty-degree rhombus."""

from ...probability.common import line
from ...triangles.right.altitude_methods import solution_section
from .rectangle_proofs import bracket, value


def _cosine(m):
    return (
        "<p>Тупой угол ромба равен разности развёрнутого и острого углов. Воспользуемся теоремой косинусов в треугольнике ABC:</p>"
        + line(r"\angle ABC=180^{\circ}-60^{\circ}=120^{\circ}")
        + line(r"AC^2=AB^2+BC^2-2AB\cdot BC\cdot\cos\angle ABC")
        + "<p>В ромбе все стороны равны. Подставим длину стороны и косинус тупого угла:</p>"
        + line(r"AC^2=2AB^2(1-\cos 120^{\circ})")
        + line(r"AC^2=2\cdot " + bracket(m.a) + r"^2\cdot(1+\frac{1}{2})")
        + line("AC^2=" + value(3 * m.a**2))
        + line(r"AC=\sqrt{" + value(3 * m.a**2) + "}=" + value(m.answer))
    )


def _sine(m):
    return (
        "<p>Тупой угол ромба равен 120°. Диагональ AC делит острые углы ромба пополам, поэтому у треугольника ABC углы 120°, 30° и 30°. По теореме синусов:</p>"
        + line(r"\angle ABC=180^{\circ}-60^{\circ}=120^{\circ}")
        + line(r"\frac{AC}{\sin 120^{\circ}}=\frac{BC}{\sin 30^{\circ}}")
        + line(r"AC=\frac{BC\sin 120^{\circ}}{\sin 30^{\circ}}")
        + "<p>Подставим длину стороны и значения синусов:</p>"
        + line(r"AC=\frac{" + value(m.a) + r"\cdot\sin 120^{\circ}}{\sin 30^{\circ}}")
        + line(r"AC=\frac{" + value(m.a) + r"\cdot\frac{\sqrt{3}}{2}}{\frac{1}{2}}")
        + line("AC=" + value(m.answer))
    )


def _half_diagonal(m):
    half = m.answer / 2
    return (
        "<p>Пусть K — точка пересечения диагоналей ромба. Диагонали перпендикулярны, поэтому треугольник ABK прямоугольный. Диагональ AC делит угол A пополам:</p>"
        + line(r"\angle BAK=\frac{60^{\circ}}{2}=30^{\circ}")
        + line(r"AK=AB\cos 30^{\circ}")
        + line("AK=" + value(m.a) + r"\cdot\frac{\sqrt{3}}{2}")
        + line("AK=" + value(half))
        + "<p>Точка пересечения делит каждую диагональ пополам. Удвоим найденный отрезок:</p>"
        + line("AC=2AK")
        + line(r"AC=2\cdot " + bracket(half) + "=" + value(m.answer))
    )


def _pythagoras(m):
    half, short = m.answer / 2, m.a / 2
    return (
        "<p>Пусть O — точка пересечения диагоналей ромба. Треугольник ABO прямоугольный. Диагональ AC делит угол A пополам. Катет против угла 30° равен половине гипотенузы:</p>"
        + line(r"\angle BAO=30^{\circ}")
        + line(r"BO=\frac{AB}{2}=\frac{" + value(m.a) + "}{2}=" + value(short))
        + "<p>Найдём отрезок AO по теореме Пифагора:</p>"
        + line("BO^2+AO^2=AB^2")
        + line(bracket(short) + "^2+AO^2=" + bracket(m.a) + "^2")
        + line("AO^2=" + value(m.a**2) + "-" + value(short**2) + "=" + value(half**2))
        + line("AO=" + value(half))
        + "<p>Диагонали точкой пересечения делятся пополам, поэтому:</p>"
        + line(r"AC=2AO=2\cdot " + bracket(half) + "=" + value(m.answer))
    )


def _area(m):
    return (
        "<p>Найдём площадь ромба двумя способами — через стороны и синус угла и через диагонали:</p>"
        + line(r"S=AB\cdot AD\sin\angle A")
        + line(r"S=\frac{DB\cdot AC}{2}")
        + "<p>В равнобедренном треугольнике ABD угол A равен 60°, поэтому треугольник равносторонний. Стороны ромба также равны. Приравняем выражения площади и сократим на положительную сторону AB:</p>"
        + line("DB=AB")
        + line("AD=AB")
        + line(r"AB^2\sin\angle A=\frac{AB\cdot AC}{2}")
        + line(r"AC=2AB\sin\angle A")
        + line(r"AC=2\cdot " + value(m.a) + r"\cdot\frac{\sqrt{3}}{2}")
        + line("AC=" + value(m.answer))
    )


def render(m):
    methods = (_cosine, _sine, _half_diagonal, _pythagoras, _area)
    return "".join(
        solution_section("Решение" if i == 0 else "Альтернативное решение.", method(m))
        for i, method in enumerate(methods)
    )
