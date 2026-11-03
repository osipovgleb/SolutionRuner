"""Height from hypotenuse and tangent, preserving both reviewed parent proofs."""

import sympy as sp

from ...probability.common import line
from ...word_problems.math_common import fraction
from .altitude_methods import review_sections, solution_section


def parent(soup):
    review_sections(
        soup,
        (
            (
                "Решение",
                (
                    r"CH=AC\sinA",
                    r"AC=AB\cosA",
                    r"CH=AB\sinA\cosA=AB\cdot\frac{\sinA}{\cosA}\cos^2A=AB\cdot\tg\alpha\frac{1}{1+\tg^2\alpha}=",
                ),
            ),
            (
                "Приведем другое решение.",
                (
                    r"x\sqrt{",
                    r"x=\frac{",
                    r"CH=\frac{CB\cdotCA}{AB}=",
                ),
            ),
        ),
    )
    return "height_tangent_methods", "CH", {"AB", "tgA"}, False, False, False


def render(solved, values, answer):
    answer = answer.replace(",", "{,}")
    factor = sp.latex(1 / dict(solved.values)["tgA"])
    root = r"\sqrt{1+(" + factor + ")^2}"
    first = (
        "<p>По определениям синуса и косинуса:</p>"
        + line(r"CH=AC\sin A")
        + line(r"AC=AB\cos A")
        + line(
            r"CH=AB\sin A\cos A=AB\cdot"
            + fraction(r"\sin A", r"\cos A")
            + r"\cos^2 A=AB\cdot\tg A\cdot"
            + fraction("1", r"1+\tg^2 A")
            + "="
            + fraction(
                "(" + values["AB"] + r")\cdot(" + values["tgA"] + ")",
                "1+(" + values["tgA"] + ")^2",
            )
            + "="
            + answer
        )
    )
    second = (
        "<p>Пусть длина катета BC равна x, где x &gt; 0. По определению тангенса:</p>"
        + line("BC=x")
        + line(r"AC=" + fraction("x", r"\tg A") + "=(" + factor + ")x")
        + "<p>По теореме Пифагора гипотенуза равна:</p>"
        + line(r"AB=\sqrt{AC^2+BC^2}=x" + root)
        + line(
            "x="
            + fraction("AB", root)
            + "="
            + fraction(values["AB"], root)
            + "="
            + values["BC"]
        )
        + "<p>Высота к гипотенузе равна произведению катетов, делённому на гипотенузу:</p>"
        + line(
            "CH="
            + fraction(r"CB\cdot CA", "AB")
            + "="
            + fraction("(" + factor + ")x^2", "x" + root)
            + "="
            + fraction("(" + factor + ")x", root)
            + "="
            + fraction("(" + factor + r")\cdot(" + values["BC"] + ")", root)
            + "="
            + answer
        )
    )
    return solution_section("Решение", first) + solution_section(
        "Приведем другое решение.", second
    )
