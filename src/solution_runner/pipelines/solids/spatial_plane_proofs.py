"""Keep the parent plane-perpendicularity and section projection methods."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def tangent_height(m, pictures):
    q = m.q
    first = "<p>Пусть O — точка пересечения AC и BD. Диагонали квадрата перпендикулярны: AC ⟂ BD. Кроме того, MO перпендикулярна основанию, поэтому AC ⟂ MO. Следовательно, AC ⟂ (MDB). Плоскость ACL содержит прямую AC, перпендикулярную плоскости MDB, поэтому эти плоскости перпендикулярны.</p>"
    second = (
        "<p>Обозначим угол между DM и AL через α. OL — средняя линия треугольника BDM, поэтому OL ∥ DM и угол ALO равен α. Из AC ⟂ (MDB) следует OA ⟂ OL, то есть треугольник AOL прямоугольный:</p>"
        + line(
            r"OA=OD=\frac{AB}{\sqrt{2}}=\frac{"
            + value(q["a"])
            + r"}{\sqrt{2}}="
            + value(q["R"])
        )
        + line(r"\tan\alpha=" + value(q["tangent"]))
        + line(r"OL=\frac{OA}{\tan\alpha}")
        + line(
            r"OL=\frac{"
            + value(q["R"])
            + "}{"
            + value(q["tangent"])
            + "}="
            + value(q["OL"])
        )
        + "<p>По свойству средней линии найдём боковое ребро, а затем высоту MO из прямоугольного треугольника MOD:</p>"
        + line(r"MD=2OL=2\cdot " + bracket(q["OL"]) + "=" + value(q["e"]))
        + line(r"MO=\sqrt{MD^2-OD^2}")
        + line(
            r"MO=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["R"])
            + "^2}="
            + value(q["H"])
        )
    )
    return picture(pictures) + parts(first, second)


def _hex_perpendicular(m):
    y, z, w, plane = m.names
    opposite = "ABCDEF"[("ABCDEF".index(y) + 3) % 6]
    lower, vertical = plane[0], plane[1]
    top = z + "_1" + w + "_1"
    base = opposite + y
    return (
        "<p>В правильном шестиугольнике "
        + base
        + " ∥ "
        + z
        + w
        + " и "
        + base
        + " ⟂ "
        + lower
        + vertical
        + ". Поэтому "
        + top.replace("_1", "₁")
        + " ⟂ "
        + lower
        + vertical
        + ". Эта горизонтальная прямая также перпендикулярна вертикальному ребру "
        + vertical
        + "₁"
        + vertical
        + ". Следовательно, "
        + top.replace("_1", "₁")
        + " перпендикулярна плоскости "
        + plane.replace("_1", "₁")
        + ". Она лежит в плоскости "
        + y
        + top.replace("_1", "₁")
        + ", поэтому требуемые плоскости перпендикулярны.</p>"
    )


def hex_prism(m, pictures):
    q = m.q
    y, z, w, _ = m.names
    opposite = "ABCDEF"[("ABCDEF".index(y) + 3) % 6]
    top = z + "_1" + w + "_1"
    base = opposite + y
    leg = y + z + "_1"
    foot = m.symbols.get("foot", "lower")
    height = y + "H" if foot == "upper" else z + "_1H"
    proof = _hex_perpendicular(m)
    small = z + "_1H" if foot == "upper" else y + "H"
    second = (
        pictures.get("image_2", "")
        + "<p>Прямая "
        + base
        + " параллельна "
        + top.replace("_1", "₁")
        + " и содержит точку "
        + y
        + ". Обозначим сторону основания через a, высоту призмы через h. Искомое расстояние равно высоте равнобедренной трапеции "
        + opposite
        + w
        + "₁"
        + z
        + "₁"
        + y
        + ". Проведём "
        + height.replace("_1", "₁")
        + " перпендикулярно её основаниям. Разность оснований делится поровну между двумя прямоугольными треугольниками:</p>"
        + line(base + r"=2a=2\cdot " + value(q["a"]) + "=" + value(2 * q["a"]))
        + line(top + "=a=" + value(q["a"]))
        + line(
            leg
            + r"=\sqrt{a^2+h^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["H"])
            + "^2}="
            + value(q["leg"])
        )
        + line(small + r"=\frac{" + base + "-" + top + "}{2}")
        + line(
            small
            + r"=\frac{"
            + value(2 * q["a"])
            + "-"
            + value(q["a"])
            + "}{2}="
            + value(q["offset"])
        )
        + "<p>По теореме Пифагора найдём высоту:</p>"
        + line(height + r"=\sqrt{" + leg + "^2-" + small + "^2}")
        + line(
            height
            + r"=\sqrt{"
            + bracket(q["leg"])
            + "^2-"
            + bracket(q["offset"])
            + "^2}="
            + value(m.answer)
        )
    )
    return pictures.get("image_1", "") + parts(proof, second)


def ratio_proof(m):
    q = m.q
    n = m.symbols.get("on_sb", "N")
    l = m.symbols.get("on_ac", "L")
    if m.mode == "ratio_plane_angle":
        return (
            "<p>Пусть α пересекает SB в точке "
            + n
            + ". Поскольку BC ∥ α, прямая "
            + n
            + "M параллельна BC. По подобию треугольников S"
            + n
            + "M и SBC отношения S"
            + n
            + " : "
            + n
            + "B и SM : MC равны, а по условию они равны AK : KB. Следовательно, K"
            + n
            + " ∥ SA. Плоскость α содержит эту прямую и потому параллельна SA.</p>"
        )
    if m.names[0] == "SB":
        return (
            "<p>Пусть α пересекает SB в точке "
            + n
            + ". Так как α ∥ SA, прямая K"
            + n
            + " параллельна SA. Из подобия треугольников "
            + n
            + "BK и SBA получаем S"
            + n
            + " : "
            + n
            + "B = AK : KB = "
            + value(q["p"])
            + " : "
            + value(q["q"])
            + ". Что и требовалось доказать.</p>"
        )
    return (
        "<p>Пусть α пересекает AC в точке "
        + l
        + ". Так как α ∥ SA, прямая "
        + l
        + "M параллельна SA. По подобию треугольников "
        + l
        + "MC и ASC имеем A"
        + l
        + " : "
        + l
        + "C = SM : MC = "
        + value(q["p"])
        + " : "
        + value(q["q"])
        + ". Что и требовалось доказать.</p>"
    )


def _ratio_lengths(m):
    q = m.q
    return (
        line(
            r"AH=\frac{AB\sqrt{3}}{2}=\frac{"
            + bracket(q["a"])
            + r"\cdot\sqrt{3}}{2}="
            + value(q["AH"])
        )
        + line(
            r"AO=\frac{AB}{\sqrt{3}}=\frac{"
            + value(q["a"])
            + r"}{\sqrt{3}}="
            + value(q["R"])
        )
        + line(
            r"SO=\sqrt{SA^2-AO^2}=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["R"])
            + "^2}="
            + value(q["H"])
        )
    )


def ratio_distance(m, pictures):
    q = m.q
    proof = ratio_proof(m)
    cross = m.symbols.get("method") == "cross_section"
    l = m.symbols.get("on_ac", "L")
    intro = (
        "<p>Пусть H — середина BC, O — центр основания. По подобию треугольников с параллельными сторонами A"
        + l
        + " : "
        + l
        + "C = AK : KB, поэтому K"
        + l
        + " ∥ BC. Плоскость SAH пересекает α по прямой, параллельной SA. Плоскость SAH перпендикулярна BC.</p>"
    )
    if cross:
        construction = "<p>Обозначим сечение α плоскостью SAH через EF, где E лежит на AH, F — на SH. Тогда EF ∥ SA и AE : EH = AK : KB. Опустим из A перпендикуляр на прямую EF и обозначим его длину d. Он перпендикулярен всей плоскости α, поскольку также перпендикулярен направлению BC. Длина d равна расстоянию между SA и α, а значит, и между SA и KM.</p>"
        segment = "AE"
        height = "d"
    else:
        construction = (
            "<p>Пусть R — точка пересечения K"
            + l
            + " и AH. Проведём RP ⟂ SA в плоскости SAH. Прямая RP перпендикулярна и направлению BC, поэтому перпендикулярна плоскости α. Она пересекает α в R, а SA — в P. Таким образом, её длина равна расстоянию между SA и α, а также расстоянию между SA и KM.</p>"
        )
        segment = "AR"
        height = "RP"
    second = (
        intro
        + construction
        + "<p>Прямая KM не параллельна SA и пересекает её ортогональную проекцию на α. Поэтому расстояния SA–α и SA–KM совпадают.</p>"
        + _ratio_lengths(m)
        + line(
            segment
            + r"=\frac{"
            + value(q["p"])
            + "}{"
            + value(q["p"] + q["q"])
            + r"}AH=\frac{"
            + value(q["p"])
            + "}{"
            + value(q["p"] + q["q"])
            + r"}\cdot "
            + bracket(q["AH"])
            + "="
            + value(q["AR"])
        )
        + pictures.get("image_2", "")
        + "<p>Искомый перпендикуляр образует с основанием угол, дополнительный к углу SAO. Поэтому его длина равна "
        + segment
        + " sin ∠SAO:</p>"
        + line(r"\sin\angle SAO=\frac{SO}{SA}")
        + line(height + "=" + segment + r"\cdot\frac{SO}{SA}")
        + line(
            height
            + "="
            + bracket(q["AR"])
            + r"\cdot\frac{"
            + value(q["H"])
            + "}{"
            + value(q["e"])
            + "}="
            + value(m.answer)
        )
    )
    return pictures.get("image_1", pictures.get("box_distance_solution", "")) + parts(
        proof, second
    )


def ratio_angle(m, pictures):
    q = m.q
    second = (
        "<p>Пусть H — середина BC. Медианы AH и SH треугольников ABC и SBC являются высотами, поэтому плоскость ASH перпендикулярна BC. Она перпендикулярна и плоскостям α и SBC. Их сечения этой плоскостью параллельны соответственно SA и SH. Значит, искомый меньший угол равен меньшему углу между SA и SH.</p>"
        + line("SA=" + value(q["e"]))
        + line(r"AH=\frac{AB\sqrt{3}}{2}=" + value(q["AH"]))
        + line(
            r"SH=\sqrt{SB^2-BH^2}=\sqrt{"
            + bracket(q["e"])
            + r"^2-\left(\frac{"
            + value(q["a"])
            + r"}{2}\right)^2}="
            + value(q["l"])
        )
        + "<p>По теореме косинусов в треугольнике ASH:</p>"
        + line(r"\cos\angle ASH=\frac{SA^2+SH^2-AH^2}{2SA\cdot SH}")
        + line(
            r"\cos\angle ASH=\frac{"
            + bracket(q["e"])
            + "^2+"
            + bracket(q["l"])
            + "^2-"
            + bracket(q["AH"])
            + r"^2}{2\cdot "
            + bracket(q["e"])
            + r"\cdot "
            + bracket(q["l"])
            + "}="
            + value((q["e"] ** 2 - q["a"] ** 2 / 2) / (q["e"] * q["l"]))
        )
        + "<p>Для меньшего угла между прямыми возьмём модуль найденного косинуса:</p>"
        + line(r"\cos\varphi=" + value(q["cosine"]))
        + line(r"\varphi=" + value(m.answer))
    )
    return picture(pictures) + parts(ratio_proof(m), second)


def render(m, pictures):
    from .spatial_projection_proof import render as projection

    return {
        "prism_projection_height": projection,
        "pyramid_skew_height": tangent_height,
        "hex_prism_distance": hex_prism,
        "ratio_plane_distance": ratio_distance,
        "ratio_plane_angle": ratio_angle,
    }[m.mode](m, pictures)
