"""Translate the skew line, apply the cosine law, and keep the child coordinates."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _side(m):
    return parts(
        "<p>По определению угол между скрещивающимися прямыми равен меньшему углу между пересекающимися прямыми, параллельными данным. Поскольку BC ∥ AD, искомый угол равен CBE.</p>",
        "<p>Примем ребро куба за единицу. Так как E — середина CC₁:</p>"
        + line(r"BC=1,\qquad CE=\frac12")
        + "<p>В прямоугольном треугольнике CBE:</p>"
        + line(r"\tan\angle CBE=\frac{CE}{BC}=\frac12"),
    )


def _claim(m):
    if m.names[4] == "coordinates":
        return "<p>Проекция прямой B₁D на основание ABCD — прямая BD. Диагонали квадрата BD и AC перпендикулярны. По теореме о трёх перпендикулярах B₁D ⟂ AC.</p>"
    _, origin, vertical, _, _ = m.names
    return (
        "<p>В грани "
        + origin
        + vertical
        + vertical
        + "₁"
        + origin
        + "₁ прямая через "
        + origin
        + "₁, параллельная "
        + origin
        + "E, пересекает продолжение ребра "
        + vertical
        + vertical
        + "₁ в F. По подобию прямоугольных треугольников "
        + vertical
        + "₁F = "
        + vertical
        + "E, то есть половина ребра куба. Это именно точка F из условия. Поэтому "
        + origin
        + "E ∥ "
        + origin
        + "₁F, и углы между указанными парами прямых равны.</p>"
    )


def _calculation(m):
    q = m.q
    _, origin, vertical, far, _ = m.names
    top, upper = origin + "_1", vertical + "_1"
    diagonal, translated, opposite = far + top, top + "F", far + "F"
    return (
        "<p>Обозначим ребро куба через a &gt; 0. Через "
        + origin
        + "₁ проведём прямую, параллельную "
        + origin
        + "E. Она проходит через F на продолжении "
        + vertical
        + vertical
        + "₁, причём "
        + vertical
        + "₁F = a/2. Искомый угол равен меньшему углу между "
        + diagonal.replace("_1", "₁")
        + " и "
        + translated.replace("_1", "₁")
        + ". По теореме Пифагора:</p>"
        + line(diagonal + r"=a\sqrt3=" + value(q["space_diagonal"]))
        + line(upper + r"F=\frac a2=" + value(q["half"]))
        + line(
            translated
            + r"=\sqrt{"
            + top
            + upper
            + "^2+"
            + upper
            + r"F^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["half"])
            + "^2}="
            + value(q["translated"])
        )
        + line(
            opposite
            + r"=\sqrt{"
            + far
            + vertical
            + "^2+"
            + vertical
            + r"F^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(3 * q["a"] / 2)
            + "^2}="
            + value(q["opposite"])
        )
        + "<p>Применим теорему косинусов к полученному треугольнику:</p>"
        + line(
            r"\cos\angle "
            + far
            + top
            + "F"
            + r"=\frac{"
            + diagonal
            + "^2+"
            + translated
            + "^2-"
            + opposite
            + r"^2}{2\cdot "
            + diagonal
            + r"\cdot "
            + translated
            + "}"
        )
        + line(
            r"\cos\angle "
            + far
            + top
            + "F"
            + r"=\frac{"
            + bracket(q["space_diagonal"])
            + "^2+"
            + bracket(q["translated"])
            + "^2-"
            + bracket(q["opposite"])
            + r"^2}{2\cdot "
            + bracket(q["space_diagonal"])
            + r"\cdot "
            + bracket(q["translated"])
            + "}="
            + value(q["cosine"])
        )
        + "<p>Косинус положителен, поэтому найденный острый угол и есть угол между данными прямыми.</p>"
    )


def _coordinates():
    return (
        "<p><b>Другой способ. Метод координат.</b> Примем ребро куба за единицу. Начало координат поместим в B, оси направим вдоль BC, BA и BB₁:</p>"
        + line(r"B(0;0;0),\quad B_1(0;0;1),\quad D(1;1;0),\quad E(1;0;\frac12)")
        + line(
            r"\overrightarrow{BE}=(1;0;\frac12),\qquad \overrightarrow{B_1D}=(1;1;-1)"
        )
        + "<p>Пусть α — меньший угол между прямыми. Найдём косинус через скалярное произведение направляющих векторов:</p>"
        + line(
            r"\cos\alpha=\frac{1\cdot1+0\cdot1+\frac12\cdot(-1)}{\sqrt{1^2+0^2+\left(\frac12\right)^2}\sqrt{1^2+1^2+(-1)^2}}=\frac{\sqrt{15}}{15}"
        )
    )


def render(m, pictures):
    if m.names[0] == "side":
        return pictures.get("image_1", "") + _side(m)
    result = parts(pictures.get("image_1", "") + _claim(m), _calculation(m))
    return result + (_coordinates() if m.names[4] == "coordinates" else "")
