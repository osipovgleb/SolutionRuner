"""Retain the cosine, Pythagorean, Heron and midpoint-projection arguments."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def _equilateral(m):
    q = m.q
    return (
        "<p>В треугольнике ADE стороны AD и AE равны, а угол DAE равен 60°, поскольку основание ABC — равносторонний треугольник. Поэтому углы при основании также равны 60°, и ADE — равносторонний треугольник:</p>"
        + line(
            "AE=AB-BE=" + value(q["a"]) + "-" + bracket(q["BE"]) + "=" + value(q["AE"])
        )
        + line("AD=AE=DE=" + value(q["AD"]))
    )


def _cosine_side(m, end, cosine, angle):
    q, p = m.q, m.names[1]
    side = "A" + end
    result = q["LD" if end == "D" else "LE"]
    return (
        "<p>По теореме косинусов в треугольнике A"
        + end
        + p
        + ":</p>"
        + line(
            p
            + end
            + r"=\sqrt{"
            + side
            + "^2+A"
            + p
            + "^2-2"
            + side
            + r"\cdot A"
            + p
            + r"\cos\angle "
            + angle
            + "}"
        )
        + line(
            p
            + end
            + r"=\sqrt{"
            + bracket(q[side])
            + "^2+"
            + bracket(q["AL"])
            + r"^2-2\cdot "
            + bracket(q[side])
            + r"\cdot "
            + bracket(q["AL"])
            + r"\cdot "
            + bracket(cosine)
            + "}="
            + value(result)
        )
    )


def _B_lengths(m):
    q, p = m.q, m.names[1]
    return (
        "<p>Прямоугольные треугольники AMB и CMB имеют общий катет MB и равные катеты AB и BC. Они равны, поэтому:</p>"
        + line("AM=MC=" + value(q["MA"]))
        + "<p>В треугольнике AMC по теореме косинусов найдём косинус угла CAM:</p>"
        + line(r"\cos\angle CAM=\frac{AM^2+AC^2-MC^2}{2AC\cdot AM}=\frac{AC}{2AM}")
        + line(
            r"\cos\angle CAM=\frac{"
            + value(q["a"])
            + r"}{2\cdot "
            + bracket(q["MA"])
            + "}="
            + value(q["a"] / (2 * q["MA"]))
        )
        + line(
            "A" + p + "=" + (r"\frac{AM}{2}=" if p == "F" else "AD=") + value(q["AL"])
        )
        + _cosine_side(m, "D", q["a"] / (2 * q["MA"]), "CAM")
        + "<p>В прямоугольном треугольнике ABM:</p>"
        + line(
            r"\cos\angle MAB=\frac{AB}{AM}=\frac{"
            + value(q["a"])
            + "}{"
            + value(q["MA"])
            + "}="
            + value(q["a"] / q["MA"])
        )
        + _cosine_side(m, "E", q["a"] / q["MA"], "MAB")
    )


def _A_lengths(m):
    q = m.q
    return (
        _equilateral(m)
        + "<p>Треугольник ABM прямоугольный. По теореме Пифагора:</p>"
        + line(
            r"AM=\sqrt{MB^2-AB^2}=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["a"])
            + "^2}="
            + value(q["MA"])
        )
        + line(
            "AL=AM-ML=" + value(q["MA"]) + "-" + bracket(q["BE"]) + "=" + value(q["AL"])
        )
        + "<p>Прямоугольные треугольники ALE и ALD равны по общему катету AL и равным катетам AE и AD. Поэтому их гипотенузы равны:</p>"
        + line(
            r"LD=LE=\sqrt{AE^2+AL^2}=\sqrt{"
            + bracket(q["AE"])
            + "^2+"
            + bracket(q["AL"])
            + "^2}="
            + value(q["LE"])
        )
        + "<p>Следовательно, треугольник LDE равнобедренный.</p>"
    )


def _sine_area(m):
    q, p = m.q, m.names[1]
    boundary = "D" + p + "E"
    return (
        "<p>Найдём косинус угла "
        + p
        + "ED по теореме косинусов, затем его синус:</p>"
        + line(
            r"\cos\angle "
            + p
            + r"ED=\frac{"
            + p
            + "E^2+DE^2-"
            + p
            + "D^2}{2"
            + p
            + r"E\cdot DE}=\frac{"
            + value(q["LE2"])
            + "+"
            + value(q["DE2"])
            + "-"
            + bracket(q["LD2"])
            + r"}{2\cdot "
            + bracket(q["LE"])
            + r"\cdot "
            + bracket(q["DE"])
            + "}="
            + value(q["cosine_E"])
        )
        + line(
            r"\sin\angle "
            + p
            + r"ED=\sqrt{1-\left(\cos\angle "
            + p
            + r"ED\right)^2}=\sqrt{1-"
            + bracket(q["cosine_E"])
            + "^2}="
            + value(q["sine_E"])
        )
        + line(
            "S_{" + boundary + r"}=\frac{1}{2}" + p + r"E\cdot DE\sin\angle " + p + "ED"
        )
        + line(
            "S_{"
            + boundary
            + r"}=\frac{1}{2}\cdot "
            + bracket(q["LE"])
            + r"\cdot "
            + bracket(q["DE"])
            + r"\cdot "
            + bracket(q["sine_E"])
            + "="
            + value(m.answer)
        )
    )


def _area(m):
    q, p = m.q, m.names[1]
    boundary = "LDE" if m.names[0] == "A" else "D" + p + "E"
    if p == "F" or (m.names[0] == "B" and sp.simplify(q["LE2"] - q["DE2"]) != 0):
        return _sine_area(m)
    if m.names[0] == "A":
        height, base, length = "LH", "DE", q["DE"]
        h = q["section_height"]
        calculation = (
            "<p>Высота LH равнобедренного треугольника LDE является медианой, поэтому EH = DE/2. По теореме Пифагора:</p>"
            + line(
                r"LH=\sqrt{LE^2-\left(\frac{DE}{2}\right)^2}=\sqrt{"
                + bracket(q["LE"])
                + r"^2-\left(\frac{"
                + value(q["DE"])
                + r"}{2}\right)^2}="
                + value(h)
            )
        )
    elif p == "L" and sp.simplify(q["LE2"] - q["DE2"]) == 0:
        height, base, length = "EH", "LD", q["LD"]
        h = sp.simplify(q["DE"] * q["section_height"] / q["LD"])
        calculation = (
            "<p>LE = DE, поэтому в равнобедренном треугольнике LDE высота EH к основанию LD является медианой. По теореме Пифагора:</p>"
            + line(
                r"EH=\sqrt{LE^2-\left(\frac{LD}{2}\right)^2}=\sqrt{"
                + bracket(q["LE"])
                + r"^2-\left(\frac{"
                + value(q["LD"])
                + r"}{2}\right)^2}="
                + value(h)
            )
        )
    return (
        calculation
        + line("S_{" + boundary + r"}=\frac{1}{2}" + height + r"\cdot " + base)
        + line(
            "S_{"
            + boundary
            + r"}=\frac{1}{2}\cdot "
            + bracket(h)
            + r"\cdot "
            + bracket(length)
            + "="
            + value(m.answer)
        )
    )


def _heron(m):
    q, p = m.q, m.names[1]
    semiperimeter = sp.simplify((q["LD"] + q["LE"] + q["DE"]) / 2)
    factors = [semiperimeter] + [
        sp.simplify(semiperimeter - q[k]) for k in ("LD", "LE", "DE")
    ]
    return (
        "<p><b>Примечание.</b> Площадь того же треугольника можно найти по формуле Герона. Обозначим полупериметр через p:</p>"
        + line(r"p=\frac{" + p + "D+" + p + r"E+DE}{2}=" + value(semiperimeter))
        + line(
            "S_{D"
            + p
            + r"E}=\sqrt{p(p-"
            + p
            + "D)(p-"
            + p
            + r"E)(p-DE)}=\sqrt{"
            + r"\cdot ".join(bracket(v) for v in factors)
            + "}="
            + value(m.answer)
        )
    )


def _projection(m, pictures):
    q = m.q
    return (
        "<p><b>Приведём другое решение пункта б).</b></p>"
        + pictures.get("image_2", "")
        + "<p>Пусть K — середина AB. Тогда FK — средняя линия треугольника ABM и параллельна MB, поэтому перпендикулярна основанию:</p>"
        + line(
            r"FK=\frac{MB}{2}=\frac{\sqrt{AM^2-AB^2}}{2}=\frac{\sqrt{"
            + bracket(q["MA"])
            + "^2-"
            + bracket(q["a"])
            + "^2}}{2}="
            + value(q["FK"])
        )
        + "<p>Опустим KN перпендикулярно DE. Из треугольника KEN:</p>"
        + line(
            r"KE=\left|AE-\frac{AB}{2}\right|=\left|"
            + value(q["AE"])
            + r"-\frac{"
            + value(q["a"])
            + r"}{2}\right|="
            + value(q["KE"])
        )
        + line(
            r"KN=KE\sin60^\circ="
            + bracket(q["KE"])
            + r"\cdot\frac{\sqrt{3}}{2}="
            + value(q["KN"])
        )
        + "<p>KN — проекция наклонной FN, поэтому по теореме о трёх перпендикулярах FN ⟂ DE. Найдём эту высоту сечения и площадь:</p>"
        + line(
            r"FN=\sqrt{FK^2+KN^2}=\sqrt{"
            + bracket(q["FK"])
            + "^2+"
            + bracket(q["KN"])
            + "^2}="
            + value(q["section_height"])
        )
        + line(
            r"S_{DFE}=\frac{1}{2}DE\cdot FN=\frac{1}{2}\cdot "
            + bracket(q["DE"])
            + r"\cdot "
            + bracket(q["section_height"])
            + "="
            + value(m.answer)
        )
    )


def render(m, pictures):
    if m.names[0] == "A":
        return picture(pictures) + parts(_A_lengths(m), _area(m))
    lengths = _B_lengths(m)
    if m.names[1] == "F":
        return picture(pictures) + parts(
            _equilateral(m), lengths + _area(m) + _heron(m) + _projection(m, pictures)
        )
    return parts(picture(pictures) + lengths + _equilateral(m), _area(m) + _heron(m))
