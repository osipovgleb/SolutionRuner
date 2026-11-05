"""Preserve the parent's geometric proof before calculating the requested distance."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from . import box_coordinates as c
from .box_distance_geometry import face_corner
from .distance_proofs import html_name, label


def parts(first, second):
    return (
        '<ol data-layout="source-subparts" type="a">'
        '<li data-list-marker="а)">' + first + "</li>"
        '<li data-list-marker="б)">' + second + "</li></ol>"
    )


def _pyramid_dimensions(m):
    q = m.q
    a, e = (value(q[k]) for k in ("a", "e"))
    known = {key for key, _ in m.given}
    dimensions = ""
    if "a" not in known:
        dimensions += line(
            r"AH=\sqrt{SA^2-SH^2}=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["H"])
            + "^2}="
            + value(q["R"])
        )
        dimensions += line(r"AB=AH\sqrt{2}=" + value(q["R"]) + r"\cdot\sqrt{2}=" + a)
    else:
        dimensions += line(
            r"AH=\frac{AB}{\sqrt{2}}=\frac{" + a + r"}{\sqrt{2}}=" + value(q["R"])
        )
    if "e" not in known:
        dimensions += line(
            r"SA=\sqrt{SH^2+AH^2}=\sqrt{"
            + bracket(q["H"])
            + "^2+"
            + bracket(q["R"])
            + "^2}="
            + e
        )
    return dimensions


def _pyramid(m, pictures):
    q = m.q
    a, apothem = (value(q[k]) for k in ("a", "l"))
    first = (
        pictures.get("image_1", "")
        + "<p>Точка H — центр квадрата ABCD, поэтому лежит на MN. Так как NC = ND, а NT перпендикулярна плоскости SCD, прямоугольные треугольники NTC и NTD имеют общую сторону NT и равные гипотенузы. Значит, TC = TD. В плоскости SCD серединным перпендикуляром к CD является SM, поэтому T лежит на SM.</p>"
        + _pyramid_dimensions(m)
        + line(r"MN=AD=AB=" + a)
        + line(r"AN=\frac{AB}{2}=" + value(q["a"] / 2))
        + line(
            r"SM=SN=\sqrt{SA^2-AN^2}=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["a"] / 2)
            + "^2}="
            + apothem
        )
        + "<p>Получили SM = SN = MN, то есть треугольник SNM равносторонний. Прямая NT перпендикулярна SM как прямой плоскости SCD. Поэтому NT — высота, а значит, и медиана треугольника SNM: T — середина SM.</p>"
    )
    second = (
        pictures.get("image_2", "")
        + "<p>Опустим из T перпендикуляр TE на SC. Он лежит в плоскости SCD, поэтому перпендикулярен NT. Таким образом, TE — общий перпендикуляр прямых NT и SC, а его длина равна искомому расстоянию.</p>"
        + line(r"ST=\frac{SM}{2}=" + value(q["ST"]))
        + line(r"MC=\frac{CD}{2}=" + value(q["MC"]))
        + "<p>Прямоугольные треугольники SET и SMC подобны по общему углу при S. Боковые рёбра SC и SA правильной пирамиды равны. Отсюда:</p>"
        + line(r"\frac{ET}{MC}=\frac{ST}{SC}")
        + line(r"ET=\frac{ST\cdot MC}{SC}=\frac{SM\cdot CD}{4SC}")
        + line(
            r"ET=\frac{"
            + bracket(q["l"])
            + r"\cdot "
            + bracket(q["a"])
            + r"}{4\cdot "
            + bracket(q["e"])
            + "}"
        )
        + line("ET=" + value(m.answer))
    )
    return parts(first, second)


def _leg_lines(m, p, last):
    leg = label(p + last)
    if len(c.axes(p + last)) == 1:
        return line(leg + "=" + value(m.q["leg"]))
    corner = face_corner(p, last)
    legs = (p + corner, corner + last)
    vals = [sp.sqrt(c.squared_length(s, m.squares)) for s in legs]
    return line(
        leg + r"=\sqrt{" + label(legs[0]) + "^2+" + label(legs[1]) + "^2}"
    ) + line(
        leg
        + r"=\sqrt{"
        + bracket(vals[0])
        + "^2+"
        + bracket(vals[1])
        + "^2}="
        + value(m.q["leg"])
    )


def _box(m, pictures):
    p, first, last = m.names
    cat, leg, hyp = (label(s) for s in (p + first, p + last, first + last))
    leg_value, cat_value, hyp_value = (m.q[k] for k in ("leg", "cathetus", "hyp"))
    height = p + "E"
    proof = (
        pictures.get("image_1", pictures.get("box_distance_solution", ""))
        + "<p>Опустим из точки "
        + html_name(p)
        + " перпендикуляр "
        + html_name(height)
        + " на прямую "
        + html_name(hyp)
        + ". Ребро "
        + html_name(cat)
        + " перпендикулярно грани, содержащей отрезок "
        + html_name(leg)
        + ", поэтому перпендикулярно и этому отрезку.</p>"
        + "<p>Следовательно, расстояние от "
        + html_name(first)
        + " до прямой "
        + html_name(leg)
        + " равно катету "
        + html_name(cat)
        + " прямоугольного треугольника "
        + html_name(first + p + last)
        + ". Второе расстояние равно его высоте "
        + html_name(height)
        + ". Высота к гипотенузе меньше каждого катета: из равенства площадей её отношение к катету равно отношению второго катета к гипотенузе, а оно меньше единицы. Требуемое неравенство доказано.</p>"
    )
    calculation = (
        "<p>Высота прямоугольного треугольника к гипотенузе равна произведению катетов, делённому на гипотенузу. Вычислим необходимые длины по теореме Пифагора:</p>"
        + _leg_lines(m, p, last)
        + line(hyp + r"=\sqrt{" + leg + "^2+" + cat + "^2}")
        + line(
            hyp
            + r"=\sqrt{"
            + bracket(leg_value)
            + "^2+"
            + bracket(cat_value)
            + "^2}="
            + value(hyp_value)
        )
        + "<p>Применим формулу высоты:</p>"
        + line(height + r"=\frac{" + leg + r"\cdot " + cat + "}{" + hyp + "}")
        + line(
            height
            + r"=\frac{"
            + bracket(leg_value)
            + r"\cdot "
            + bracket(cat_value)
            + "}{"
            + value(hyp_value)
            + "}"
        )
        + line(height + "=" + value(m.answer))
    )
    return parts(proof, calculation)


def render(m, pictures):
    from . import (
        adjacent_midpoint_proof,
        box_bisector_cut_proof,
        box_opposite_cut_proof,
        cube_plane_section_model,
        cube_plane_section_proofs,
        prism_diagonal_cut_model,
        prism_diagonal_cut_proof,
        prism_midpoint_cut_model,
        prism_midpoint_cut_proof,
        prism_oblique_height_proof,
        prism_pentagon_cut_model,
        prism_pentagon_cut_proof,
        prism_perpendicular_cut_proof,
        prism_separation_model,
        prism_separation_proofs,
        prism_similarity_cut_model,
        prism_similarity_cut_proof,
        pyramid_inverse_section_proof,
        pyramid_midline_ratio_proof,
        pyramid_midsection_model,
        pyramid_midsection_proofs,
        pyramid_perpendicular_section_model,
        pyramid_perpendicular_section_proof,
        pyramid_vertical_cut_model,
        pyramid_vertical_cut_proof,
        reflected_section_proofs,
        regular_triangle_cut_model,
        regular_triangle_cut_proof,
        right_pyramid_cut_model,
        right_pyramid_cut_proof,
        spatial_altitude_model,
        spatial_altitude_proofs,
        spatial_metric_model,
        spatial_metric_proofs,
        spatial_plane_model,
        spatial_plane_proofs,
        spatial_section_model,
        spatial_section_proofs,
    )

    direct = {
        "box_diagonal_bisector_ratio": box_bisector_cut_proof,
        "box_opposite_section_area": box_opposite_cut_proof,
        "triangle_prism_oblique_height": prism_oblique_height_proof,
        "triangle_prism_perpendicular_area": prism_perpendicular_cut_proof,
        "triangle_prism_perpendicular_height": prism_perpendicular_cut_proof,
        "square_perpendicular_section_ratio": pyramid_inverse_section_proof,
        "pyramid_midline_ratio": pyramid_midline_ratio_proof,
        "square_adjacent_midpoint_area": adjacent_midpoint_proof,
        "reflected_triangle_section_midline": reflected_section_proofs,
        "reflected_square_section_midline": reflected_section_proofs,
    }
    if m.mode in direct:
        return direct[m.mode].render(m, pictures)
    for family, proof in (
        (prism_diagonal_cut_model, prism_diagonal_cut_proof),
        (prism_pentagon_cut_model, prism_pentagon_cut_proof),
        (prism_similarity_cut_model, prism_similarity_cut_proof),
        (prism_midpoint_cut_model, prism_midpoint_cut_proof),
        (regular_triangle_cut_model, regular_triangle_cut_proof),
        (right_pyramid_cut_model, right_pyramid_cut_proof),
    ):
        if m.mode in family.MODES:
            return proof.render(m, pictures)
    if m.mode in pyramid_vertical_cut_model.MODES:
        return pyramid_vertical_cut_proof.render(m, pictures)
    if m.mode in pyramid_perpendicular_section_model.MODES:
        return pyramid_perpendicular_section_proof.render(m, pictures)
    if m.mode in pyramid_midsection_model.MODES:
        return pyramid_midsection_proofs.render(m, pictures)
    if m.mode in spatial_section_model.MODES:
        return spatial_section_proofs.render(m, pictures)
    if m.mode in cube_plane_section_model.MODES:
        return cube_plane_section_proofs.render(m, pictures)
    if m.mode in spatial_altitude_model.MODES:
        return spatial_altitude_proofs.render(m, pictures)
    if m.mode in prism_separation_model.MODES:
        return prism_separation_proofs.render(m, pictures)
    if m.mode in spatial_plane_model.MODES:
        return spatial_plane_proofs.render(m, pictures)

    if m.mode in spatial_metric_model.MODES:
        return spatial_metric_proofs.render(m, pictures)
    return (
        _pyramid(m, pictures)
        if m.mode == "pyramid_skew_midpoint"
        else _box(m, pictures)
    )
