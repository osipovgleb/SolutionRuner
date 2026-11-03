"""The parent's acute-angle definitions and inverse base calculations."""

from ...probability.common import line
from ..parallelogram.rectangle_proofs import bracket, value
from .isosceles_area_proofs import height_rows, projection_rows


def _sine(m):
    return (
        "<p>Пусть отрезок CE — высота трапеции. В равнобедренной трапеции ED равен половине разности оснований:</p>"
        + projection_rows(m, "ED")
        + "<p>По теореме Пифагора в прямоугольном треугольнике CED найдём CE:</p>"
        + height_rows(m, "CD", "CE", "ED")
        + "<p>По определению синуса острого угла:</p>"
        + line(r"\sin\angle CDA=\frac{CE}{CD}")
        + line(
            r"\sin\angle CDA=\frac{"
            + value(m.height)
            + "}{"
            + value(m.leg)
            + "}="
            + value(m.sine)
        )
    )


def _cosine_leg(m):
    return (
        "<p>Пусть отрезок CE — высота трапеции. В треугольнике CED найдём прилежащий катет ED:</p>"
        + projection_rows(m, "ED")
        + "<p>По определению косинуса выразим гипотенузу CD — боковую сторону трапеции:</p>"
        + line(r"\cos\angle CDA=\frac{ED}{CD}")
        + line(r"CD\cos\angle CDA=ED")
        + line(r"CD=\frac{ED}{\cos\angle CDA}")
        + line(
            r"CD=\frac{"
            + value(m.projection)
            + "}{"
            + value(m.cosine)
            + "}="
            + value(m.leg)
        )
    )


def _small_sine(m):
    return (
        "<p>Проведём высоту CE. В равнобедренной трапеции ED равен половине разности оснований. Поэтому последовательно получаем:</p>"
        + line("BC=AD-2ED")
        + line(r"ED=CD\cos\angle CDA")
        + "<p>Острый угол имеет положительный косинус. Выразим его через данный синус:</p>"
        + line(r"\cos\angle CDA=\sqrt{1-\sin^2\angle CDA}")
        + line(r"\cos\angle CDA=\sqrt{1-" + bracket(m.sine) + "^2}")
        + line(r"\cos\angle CDA=" + value(m.cosine))
        + "<p>Найдём ED и вычтем два таких отрезка из большего основания:</p>"
        + line(
            "ED="
            + value(m.leg)
            + r"\cdot "
            + bracket(m.cosine)
            + "="
            + value(m.projection)
        )
        + line(
            "BC="
            + value(m.large)
            + r"-2\cdot "
            + bracket(m.projection)
            + "="
            + value(m.small)
        )
    )


def _tangent_height(m):
    return (
        "<p>Проведём высоту CE. По определению тангенса в прямоугольном треугольнике CED:</p>"
        + line(r"CE=ED\tg\angle CDA")
        + "<p>В равнобедренной трапеции ED равен полуразности оснований. Найдём его и подставим в выражение высоты:</p>"
        + projection_rows(m, "ED")
        + line("CE=" + value(m.projection) + r"\cdot " + bracket(m.tangent))
        + line("CE=" + value(m.height))
    )


def _large_tangent(m):
    return (
        "<p>Проведём высоту CE. В равнобедренной трапеции большее основание равно сумме меньшего основания и двух отрезков ED:</p>"
        + line("AD=BC+2ED")
        + "<p>По определению тангенса выразим ED через данную высоту CE и тангенс острого угла:</p>"
        + line(r"\tg\angle CDA=\frac{CE}{ED}")
        + line(r"ED=\frac{CE}{\tg\angle CDA}")
        + line(
            r"ED=\frac{"
            + value(m.height)
            + "}{"
            + value(m.tangent)
            + "}="
            + value(m.projection)
        )
        + "<p>Подставим ED в выражение большего основания:</p>"
        + line(
            "AD="
            + value(m.small)
            + r"+2\cdot "
            + bracket(m.projection)
            + "="
            + value(m.large)
        )
    )


def _tangent(m):
    return (
        "<p>Проведём высоту CE. По определению тангенса в прямоугольном треугольнике CED:</p>"
        + line(r"\tg\angle CDA=\frac{CE}{ED}")
        + "<p>Найдём ED как половину разности оснований и подставим данную высоту:</p>"
        + projection_rows(m, "ED")
        + line("CE=" + value(m.height))
        + line(
            r"\tg\angle CDA=\frac{" + value(m.height) + "}{" + value(m.projection) + "}"
        )
        + line(r"\tg\angle CDA=" + value(m.tangent))
    )


def _small_sixty(m):
    return (
        "<p>Проведём высоту BH. Полуразность оснований равна отрезку AH, поэтому:</p>"
        + line("BC=AD-2AH")
        + "<p>По определению косинуса в прямоугольном треугольнике ABH найдём AH:</p>"
        + line(r"AH=AB\cos\angle BAD")
        + line("AB=" + value(m.leg))
        + line(r"\cos 60^{\circ}=\frac{1}{2}")
        + line("AH=" + value(m.leg) + r"\cdot\frac{1}{2}=" + value(m.projection))
        + "<p>Подставим найденный отрезок в выражение меньшего основания:</p>"
        + line(
            "BC="
            + value(m.large)
            + r"-2\cdot "
            + bracket(m.projection)
            + "="
            + value(m.small)
        )
    )


def _fortyfive(m):
    return (
        "<p>Проведём высоту BH. По определению тангенса в прямоугольном треугольнике ABH последовательно получаем:</p>"
        + line(r"BH=AH\tg\angle BAD")
        + "<p>В равнобедренной трапеции AH равен половине разности оснований:</p>"
        + projection_rows(m)
        + line(r"\tg45^{\circ}=1")
        + "<p>Подставим найденный катет и значение тангенса 45°:</p>"
        + line("BH=" + value(m.projection) + r"\cdot1=" + value(m.height))
    )


def render(m):
    method = {
        "sine": _sine,
        "cosine_leg": _cosine_leg,
        "small_sine": _small_sine,
        "tangent_height": _tangent_height,
        "large_tangent": _large_tangent,
        "tangent": _tangent,
        "small_sixty": _small_sixty,
        "height_fortyfive": _fortyfive,
    }[m.mode]
    return method(m)
