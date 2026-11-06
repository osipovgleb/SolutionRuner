"""The parent common-perpendicular proof and angle between normals."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def render(m, pictures):
    q = m.q
    proof = (
        pictures.get("image_1", "")
        + "<p>Пусть O — точка пересечения диагоналей основания, а O₁ — расположенная над ней точка пересечения диагоналей верхнего основания. Прямая AC проходит через O, прямая B₁D₁ — через O₁. Отрезок OO₁ вертикален, поэтому перпендикулярен обеим прямым. Он является их общим перпендикуляром, и расстояние между прямыми равно высоте призмы. Для прямых A₁D₁ и BD общим перпендикуляром является DD₁. Его длина равна той же высоте. Следовательно, требуемые расстояния равны.</p>"
    )
    quantity = (
        "<p>Из данного расстояния находим высоту призмы:</p>"
        + line(r"DD_1=" + value(q["height"]))
        + "<p>Угол между плоскостями равен меньшему углу между их нормалями. Нормаль к основанию направлена вдоль DD₁, а нормаль к заданной плоскости — вдоль BD₁. Поэтому рассмотрим прямоугольный треугольник BDD₁:</p>"
        + line(
            r"BD=\sqrt{AB^2+AD^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["b"])
            + "^2}="
            + value(q["base_diagonal"])
        )
        + line(r"\tan\angle BD_1D=\frac{BD}{DD_1}")
        + line(
            r"\tan\angle BD_1D=\frac{"
            + bracket(q["base_diagonal"])
            + "}{"
            + bracket(q["height"])
            + "}="
            + value(q["tan"])
        )
    )
    return parts(proof, quantity)
