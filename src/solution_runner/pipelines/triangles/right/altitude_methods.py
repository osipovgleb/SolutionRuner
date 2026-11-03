"""Reviewed multiple-method altitude proofs sharing the exact inferred values."""

from ...probability.common import line
from ...word_problems.math_common import fraction
from .altitude_solver import AltitudeSolveError


def tangent_parent(soup):
    sections = soup.select('section[data-content-kind="solution"]')
    expected = (
        (r"BH=CH\tg\angleHCB=CH\tgA=AH\tg^2A=",),
        (
            r"\tgA=\frac{CH}{AH}",
            r"CH=AH\cdot\tgA=",
            r"CH^2=AH\cdotHB",
            r"BH=\frac{CH^2}{AH}=",
        ),
    )
    if (
        len(sections) != 2
        or len(soup.select("[data-inline-latex]")) != 5
        or soup.find("img")
    ):
        raise AltitudeSolveError("every parent method must be reviewed")
    for section, prefixes in zip(sections, expected, strict=True):
        forms = [
            "".join(node["data-inline-latex"].split()).replace("^{2}", "^2")
            for node in section.select("[data-inline-latex]")
        ]
        if len(forms) != len(prefixes) or any(
            not formula.startswith(prefix)
            for formula, prefix in zip(forms, prefixes, strict=True)
        ):
            raise AltitudeSolveError("every parent method must be reviewed")
    if [s.get("data-solution-title") for s in sections] != [
        "Решение",
        "Приведем другое решение.",
    ]:
        raise AltitudeSolveError("the parent method titles have not been reviewed")
    return "tangent_bh_methods", "BH", {"AH", "tgA"}, False, False, False


def tangent_solutions(values, answer):
    def section(title, body):
        return (
            '<section data-content-kind="solution" data-solution-title="'
            + title
            + '">'
            + body
            + "</section>"
        )

    answer = answer.replace(",", "{,}")
    first = (
        "<p>Углы A и HCB равны как углы со взаимно перпендикулярными сторонами. "
        "Из треугольников BHC и ACH имеем:</p>"
        + line(
            r"BH=CH\tg\angle HCB=CH\tg A=AH\tg^2 A="
            + "("
            + values["AH"]
            + r")\cdot("
            + values["tgA"]
            + ")^2="
            + answer
        )
    )
    second = (
        "<p>Из треугольника ACH по определению тангенса находим:</p>"
        + line(r"\tg A=" + fraction("CH", "AH"))
        + line(
            r"CH=AH\cdot\tg A=("
            + values["AH"]
            + r")\cdot("
            + values["tgA"]
            + ")="
            + values["CH"]
        )
        + "<p>По свойству высоты прямоугольного треугольника, проведённой к гипотенузе:</p>"
        + line(r"CH^2=AH\cdot HB")
        + line(
            "BH="
            + fraction("CH^2", "AH")
            + "="
            + fraction("(" + values["CH"] + ")^2", values["AH"])
            + "="
            + answer
        )
    )
    return section("Решение", first) + section("Приведем другое решение.", second)
