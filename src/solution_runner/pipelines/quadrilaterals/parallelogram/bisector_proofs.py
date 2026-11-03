"""Follow the parent bisector, isosceles-triangle and adjacent-angle arguments."""

from ...probability.common import line
from ...triangles.right.altitude_methods import solution_section
from .bisector_model import RhombusAngle, is_half
from .rectangle_proofs import value


def _ratio(m):
    first, second, perimeter = m.given
    x = perimeter / (2 * (2 * first + second))
    return (
        "<p>Углы CBL и ALB равны как накрест лежащие при пересечении параллельных прямых BC и AD секущей BL. Луч BL — биссектриса, поэтому:</p>"
        + line(r"\angle ABL=\angle CBL=\angle ALB")
        + "<p>Следовательно, треугольник ABL равнобедренный, AB=AL. Пусть AL=r·x, LD=s·x, где r:s — данное отношение, отсчитываемое от вершины острого угла A:</p>"
        + line("AL=" + value(first) + r"x,\quad LD=" + value(second) + "x")
        + line("AB=AL=" + value(first) + "x")
        + line("AD=AL+LD=" + value(first + second) + "x")
        + "<p>Противоположные стороны параллелограмма попарно равны. Подставим стороны в формулу периметра:</p>"
        + line("P=2(AD+AB)")
        + line(value(2 * (2 * first + second)) + "x=" + value(perimeter))
        + line(
            r"x=\frac{"
            + value(perimeter)
            + "}{"
            + value(2 * (2 * first + second))
            + "}="
            + value(x)
        )
        + "<p>Так как LD положителен, AD=AB+LD больше AB. Найдём искомую сторону:</p>"
        + line(
            "AD=" + value(first + second) + r"\cdot " + value(x) + "=" + value(m.answer)
        )
    )


def _double(m):
    return (
        "<p>Обозначим точку пересечения биссектрис E; она лежит на стороне AD. Углы CBE и BEA равны как накрест лежащие при пересечении параллельных AD и BC секущей BE. Кроме того, BE — биссектриса:</p>"
        + line(r"\angle CBE=\angle BEA")
        + line(r"\angle ABE=\angle CBE")
        + line(r"\angle ABE=\angle BEA")
        + "<p>Треугольник ABE равнобедренный, поэтому AE=AB. Аналогично, используя биссектрису CE и параллельность сторон, получаем равнобедренный треугольник CDE:</p>"
        + line(r"\angle BCE=\angle CED=\angle ECD")
        + line("AE=AB")
        + line("DE=DC")
        + "<p>В параллелограмме AB=DC. Значит, AD=AE+DE=2AB, и меньшей стороной является AB. Подставим её данную длину:</p>"
        + line("AE=AB=" + value(m.first))
        + line("DE=DC=" + value(m.first))
        + line(
            "AD=AE+DE=" + value(m.first) + "+" + value(m.first) + "=" + value(m.answer)
        )
    )


def _rhombus(m):
    known, target = m.known[1], m.target[1]
    known_full, target_full = m.full(known), m.full(target)
    result = line(r"\angle " + m.known + "=" + value(m.amount))
    if is_half(m.known):
        result += (
            "<p>Диагональ ромба является биссектрисой угла "
            + known
            + ". Удвоим данный угол, чтобы найти полный угол ромба:</p>"
            + line(r"\angle " + known + r"=2\angle " + m.known)
            + line(
                r"\angle "
                + known
                + r"=2\cdot "
                + value(m.amount)
                + "="
                + value(known_full)
            )
        )
    else:
        result += line(
            r"\angle " + known + r"=\angle " + m.known + "=" + value(known_full)
        )
    if target != known:
        if (target in "AC") == (known in "AC"):
            result += "<p>Противоположные углы ромба равны:</p>" + line(
                r"\angle " + target + r"=\angle " + known + "=" + value(target_full)
            )
        else:
            result += (
                "<p>Сумма соседних углов ромба равна 180°. Найдём угол "
                + target
                + ":</p>"
                + line(r"\angle " + known + r"+\angle " + target + r"=180^{\circ}")
                + line(r"\angle " + target + r"=180^{\circ}-\angle " + known)
                + line(
                    r"\angle "
                    + target
                    + r"=180^{\circ}-"
                    + value(known_full)
                    + "="
                    + value(target_full)
                )
            )
    if is_half(m.target):
        result += (
            "<p>Диагональ ромба является биссектрисой угла "
            + target
            + ", поэтому искомый угол равен половине полного:</p>"
            + line(r"\angle " + m.target + r"=\frac{\angle " + target + "}{2}")
            + line(
                r"\angle "
                + m.target
                + r"=\frac{"
                + value(target_full)
                + "}{2}="
                + value(m.answer)
            )
        )
    else:
        result += line(
            r"\angle " + m.target + r"=\angle " + target + "=" + value(m.answer)
        )
    return result


def render(m, pictures):
    if isinstance(m, RhombusAngle):
        html = pictures["reference"] + _rhombus(m)
    else:
        html = _ratio(m) if m.mode == "bisector_ratio" else _double(m)
    return solution_section("Решение", html)
