"""Retain the complementary-angle proof, including its 30-degree special case."""

import re
import unicodedata

import sympy as sp

from ...probability.common import line
from ...word_problems.math_common import fraction
from .altitude_methods import review_sections, solution_section
from .altitude_solver import AltitudeSolveError


def parent(soup):
    review_sections(
        soup,
        (
            ("Решение", (r"CH=BC\cos\widehat{HCB}=BC\cosA=",)),
            ("Приведем другое решение.", ()),
        ),
    )
    text = " ".join(
        unicodedata.normalize(
            "NFKC", soup.select("section")[1].get_text(" ", strip=True)
        )
        .replace("\xad", "")
        .replace("АВС", "ABC")
        .split()
    )
    number = r"\d+(?:[,.]\d+)?"
    expected = (
        r"В прямоугольном треугольнике ABC угол A равен 60°, поэтому угол B равен 30°. "
        r"Но это острый угол в треугольнике HCB , поэтому катет CH в нем вдвое меньше "
        r"гипотенузы BC , по условию равной "
        + number
        + r"\. Таким образом, CH = "
        + number
        + r"\."
    )
    if re.fullmatch(expected, text) is None:
        raise AltitudeSolveError(
            "the complete complementary-angle argument must be reviewed"
        )
    return "complementary_height_methods", "CH", {"BC", "cosA"}, False, False, False


def render(solved, values, answer):
    answer = answer.replace(",", "{,}")
    first = (
        "<p>Углы A и HCB равны как углы со взаимно перпендикулярными сторонами.</p>"
        + line(
            r"CH=BC\cos\angle HCB=BC\cos A=("
            + values["BC"]
            + r")\cdot("
            + values["cosA"]
            + ")="
            + answer
        )
    )
    if dict(solved.values)["cosA"] == sp.Rational(1, 2):
        second = (
            "<p>В прямоугольном треугольнике ABC угол A равен 60°, поэтому угол B равен 30°. "
            "В прямоугольном треугольнике HCB катет CH лежит против угла B и равен половине гипотенузы BC:</p>"
            + line(
                "CH="
                + fraction("BC", "2")
                + "="
                + fraction(values["BC"], "2")
                + "="
                + answer
            )
        )
    else:
        second = (
            "<p>В прямоугольном треугольнике ABC углы A и B в сумме равны 90°. "
            "Поэтому синус угла B равен косинусу угла A:</p>"
            + line(r"\sin B=\cos A=" + values["cosA"])
            + "<p>В прямоугольном треугольнике HCB катет CH лежит против угла B. По определению синуса:</p>"
            + line(
                "CH="
                + r"BC\sin B=("
                + values["BC"]
                + r")\cdot("
                + values["cosA"]
                + ")="
                + answer
            )
        )
    return solution_section("Решение", first) + solution_section(
        "Приведем другое решение.", second
    )
