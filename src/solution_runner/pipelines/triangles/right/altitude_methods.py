"""Reviewed multiple-method altitude proofs sharing the exact inferred values."""

from ...probability.common import line
from ...word_problems.math_common import fraction
from .altitude_solver import AltitudeSolveError


def review_sections(soup, expected):
    sections = soup.select('section[data-content-kind="solution"]')
    if (
        len(sections) != len(expected)
        or len(soup.select("[data-inline-latex]"))
        != sum(len(forms) for _, forms in expected)
        or soup.find("img")
    ):
        raise AltitudeSolveError("every parent method must be reviewed")
    for section, (title, prefixes) in zip(sections, expected, strict=True):
        forms = [
            "".join(node["data-inline-latex"].split()).replace("^{2}", "^2")
            for node in section.select("[data-inline-latex]")
        ]
        if (
            section.get("data-solution-title") != title
            or len(forms) != len(prefixes)
            or any(
                not formula.startswith(prefix)
                for formula, prefix in zip(forms, prefixes, strict=True)
            )
        ):
            raise AltitudeSolveError("every parent method must be reviewed")


def multiple_parent(soup):
    first = soup.select_one("[data-inline-latex]")
    if first is not None and first["data-inline-latex"].startswith("AH="):
        from .altitude_projection_methods import parent

        return parent(soup)
    review_sections(
        soup,
        (
            ("Решение", (r"BH=CH\tg\angleHCB=CH\tgA=AH\tg^2A=",)),
            (
                "Приведем другое решение.",
                (
                    r"\tgA=\frac{CH}{AH}",
                    r"CH=AH\cdot\tgA=",
                    r"CH^2=AH\cdotHB",
                    r"BH=\frac{CH^2}{AH}=",
                ),
            ),
        ),
    )
    return "tangent_bh_methods", "BH", {"AH", "tgA"}, False, False, False


def solution_section(title, body):
    return (
        '<section data-content-kind="solution" data-solution-title="'
        + title
        + '">'
        + body
        + "</section>"
    )


def tangent_solutions(values, answer):
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
    return solution_section("Решение", first) + solution_section(
        "Приведем другое решение.", second
    )
