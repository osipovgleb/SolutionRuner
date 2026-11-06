"""Prove the vertex altitude first; retain the reviewed geometric angle construction."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_altitude_proofs import _rectangular_proof
from .spatial_distance_proofs import parts


def _extended_side(m):
    q = m.q
    return (
        "<p>На продолжении AB за точку B отметим E так, чтобы BE = AB. Тогда BDCE — параллелограмм, CE ∥ BD и CE = BD. Угол между SC и BD равен меньшему углу между прямыми SC и CE. Найдём косинус угла SCE.</p>"
        + line(
            r"AC=BD=CE=\sqrt{AB^2+AD^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["b"])
            + "^2}="
            + value(q["AC"])
        )
        + line(
            r"SC=\sqrt{SA^2+AC^2}=\sqrt{"
            + bracket(q["H"])
            + "^2+"
            + bracket(q["AC"])
            + "^2}="
            + value(q["SC"])
        )
        + line(r"AE=2AB=" + value(2 * q["a"]))
        + line(
            r"SE^2=SA^2+AE^2="
            + bracket(q["H"])
            + "^2+"
            + bracket(2 * q["a"])
            + "^2="
            + value(q["SE_squared"])
        )
        + "<p>По теореме косинусов в треугольнике SCE:</p>"
        + line(r"\cos\angle SCE=\frac{SC^2+CE^2-SE^2}{2SC\cdot CE}")
        + line(
            r"\cos\angle SCE=\frac{"
            + bracket(q["SC"])
            + "^2+"
            + bracket(q["AC"])
            + "^2-"
            + bracket(q["SE_squared"])
            + r"}{2\cdot "
            + bracket(q["SC"])
            + r"\cdot "
            + bracket(q["AC"])
            + "}="
            + value(q["cosine"])
        )
        + "<p>Для меньшего угла между прямыми берём модуль найденного косинуса.</p>"
    )


def _median(m):
    q = m.q
    return (
        "<p>Пусть O — точка пересечения диагоналей основания, K — середина SA. В треугольнике SAC отрезок OK — средняя линия, поэтому OK ∥ SC. Значит, искомый угол — меньший угол между прямыми OK и BD.</p>"
        + line(r"AC=BD=\sqrt{AB^2+AD^2}=" + value(q["AC"]))
        + line(r"SC=\sqrt{SA^2+AC^2}=" + value(q["SC"]))
        + line(
            r"BK=\sqrt{AB^2+AK^2}=\sqrt{"
            + bracket(q["a"])
            + r"^2+\left(\frac{"
            + value(q["H"])
            + r"}{2}\right)^2}="
            + value(q["BK"])
        )
        + line(r"OB=\frac{BD}{2}=" + value(q["OB"]))
        + line(r"OK=\frac{SC}{2}=" + value(q["OK"]))
        + "<p>Применим теорему косинусов к треугольнику BOK:</p>"
        + line(r"\cos\angle BOK=\frac{OB^2+OK^2-BK^2}{2OB\cdot OK}")
        + line(
            r"\cos\angle BOK=\frac{"
            + bracket(q["OB"])
            + "^2+"
            + bracket(q["OK"])
            + "^2-"
            + bracket(q["BK"])
            + r"^2}{2\cdot "
            + bracket(q["OB"])
            + r"\cdot "
            + bracket(q["OK"])
            + "}="
            + value(q["cosine"])
        )
        + "<p>Для меньшего угла между прямыми берём модуль косинуса угла BOK.</p>"
    )


def _coordinates(m, picture):
    q = m.q
    return (
        picture
        + "<p><b>Другой способ. Метод координат.</b> Поместим начало координат в A, ось x направим по AD, ось y — по AB, ось z — по AS. Пусть α — меньший угол между SC и BD:</p>"
        + line(
            "S(0;0;"
            + value(q["H"])
            + r"),\quad B(0;"
            + value(q["a"])
            + r";0),\quad C("
            + value(q["b"])
            + ";"
            + value(q["a"])
            + r";0),\quad D("
            + value(q["b"])
            + ";0;0)"
        )
        + line(
            r"\overrightarrow{SC}=("
            + value(q["b"])
            + ";"
            + value(q["a"])
            + ";-"
            + bracket(q["H"])
            + r"),\qquad \overrightarrow{BD}=("
            + value(q["b"])
            + ";-"
            + bracket(q["a"])
            + ";0)"
        )
        + line(
            r"\cos\alpha=\frac{|\overrightarrow{SC}\cdot\overrightarrow{BD}|}{|\overrightarrow{SC}|\cdot|\overrightarrow{BD}|}"
        )
        + line(
            r"\cos\alpha=\frac{|"
            + bracket(q["b"])
            + "^2-"
            + bracket(q["a"])
            + r"^2|}{"
            + bracket(q["SC"])
            + r"\cdot "
            + bracket(q["AC"])
            + "}=|"
            + value(q["cosine"])
            + "|"
        )
    )


def render(m, pictures):
    picture = pictures.get("image_1", pictures.get("box_distance_solution", ""))
    second = _median(m) if m.symbols.get("method") == "median" else _extended_side(m)
    result = parts(picture + _rectangular_proof(m), second)
    if "image_2" in pictures:
        result += _coordinates(m, pictures["image_2"])
    return result
