"""Three parent methods for hypotenuse projections from the tangent."""

import re

from ...probability.common import line
from ...word_problems.math_common import fraction
from .altitude_methods import review_sections, solution_section


def parent(soup):
    first = soup.select_one("[data-inline-latex]")["data-inline-latex"]
    ah = first.startswith("AH=")
    if ah:
        expected = (
            (
                "Решение",
                (r"AH=AC\cosA=(AB\cosA)\cosA=AB\cos^2A=AB\cdot\frac{1}{1+\tg^2A}=",),
            ),
            (
                "Альтернативное решение.",
                (
                    r"\tgA=\frac{CH}{AH}",
                    re.compile(r"\\frac\{\d+\}\{\d+\}=\\frac\{CH\}\{AH\}"),
                    r"CH=\frac{AH}{",
                    r"CH^2=AH\cdotHB",
                    "AH=x",
                    "HB=",
                    re.compile(r"\(\\frac\{x\}\{\d+\}\)\^2=x\("),
                    "x=0",
                    re.compile(r"\d+x-\d+=0\\iff\d+x=\d+\\iffx="),
                ),
            ),
            (
                "Альтернативное решение.",
                (
                    "AH=x",
                    "HB=",
                    r"CH=AH\cdot\tgA=",
                    r"CH=\frac{BH}{\tgA}=",
                    re.compile(r"\\frac\{x\}\{\d+\}=\d+\(\d+-x\)\\iff"),
                ),
            ),
        )
    else:
        expected = (
            (
                "Решение",
                (
                    r"BH=CB\sin\widehat{HCB}=CB\sinA=AB\sin^2A=AB(1-\cos^2A)=AB(1-\frac{1}{1+\tg^2A})=",
                ),
            ),
            (
                "Альтернативное решение.",
                (
                    r"CH=AH\tgA=(",
                    r"CH=\frac{BH}{\tgA}=\frac{x}{\tgA}",
                    re.compile(r"\d+\(\d+-x\)=\\frac\{x\}\{\d+\}\\iff"),
                ),
            ),
            (
                "Альтернативное решение.",
                (
                    r"\tgA=\frac{BC}{AC}",
                    re.compile(r"BC=\d+AC"),
                    r"AC^2+BC^2=AB^2",
                    re.compile(r"AC\^2\+\(\d+AC\)\^2=\d+\^2\\iffAC=\\sqrt"),
                    r"\cosA=\frac{AC}{AB}=",
                    r"\cosA=\frac{AH}{AC}\iffAH=AC\cdot\cosA=",
                    "BH=AB-AH=",
                ),
            ),
        )
    review_sections(soup, expected)
    return (
        "hypotenuse_" + ("ah" if ah else "bh") + "_methods",
        "AH" if ah else "BH",
        {"AB", "tgA"},
        False,
        False,
        False,
    )


def _trigonometry(values, answer, ah):
    if ah:
        formula = (
            r"AH=AC\cos A=(AB\cos A)\cos A=AB\cos^2 A="
            + fraction("AB", r"1+\tg^2 A")
            + "="
            + fraction(values["AB"], "1+(" + values["tgA"] + ")^2")
        )
    else:
        formula = (
            r"BH=CB\sin\angle HCB=CB\sin A=AB\sin^2 A=AB(1-\cos^2 A)="
            + "AB(1-"
            + fraction("1", r"1+\tg^2 A")
            + ")="
            + fraction(r"AB\tg^2 A", r"1+\tg^2 A")
            + "="
            + fraction(
                "(" + values["AB"] + ")(" + values["tgA"] + ")^2",
                "1+(" + values["tgA"] + ")^2",
            )
        )
    return (
        "<p>По определениям тригонометрических функций и основным тождествам:</p>"
        + line(formula + "=" + answer)
    )


def _metric_equation(values, answer):
    return (
        "<p>Из треугольника ACH по определению тангенса:</p>"
        + line(r"\tg A=" + fraction("CH", "AH"))
        + line(r"CH=AH\tg A")
        + "<p>По свойству высоты прямоугольного треугольника:</p>"
        + line(r"CH^2=AH\cdot HB")
        + "<p>Пусть AH = x, где x &gt; 0. Тогда:</p>"
        + line("AH=x")
        + line("HB=AB-x=" + values["AB"] + "-x")
        + line(
            r"(x\tg A)^2=x(AB-x)\iff x^2\tg^2 A=AB\cdot x-x^2\iff x((1+\tg^2 A)x-AB)=0"
        )
        + "<p>Корень x = 0 не подходит, поскольку AH &gt; 0. Поэтому:</p>"
        + line(
            r"(1+\tg^2 A)x=AB\iff x="
            + fraction("AB", r"1+\tg^2 A")
            + "="
            + fraction(values["AB"], "1+(" + values["tgA"] + ")^2")
            + "="
            + answer
        )
    )


def _two_heights(values, answer, ah):
    left, right = ("AH", "HB") if ah else ("BH", "AH")
    intro = "<p>Пусть " + left + " = x, где x &gt; 0. Тогда:</p>"
    body = line(left + "=x") + line(right + "=AB-x=" + values["AB"] + "-x")
    body += "<p>Выразим CH через тангенс в треугольниках ACH и BCH:</p>"
    if ah:
        rows = (
            r"CH=AH\tg A=x\tg A",
            r"CH=" + fraction("BH", r"\tg A") + "=" + fraction("AB-x", r"\tg A"),
            r"x\tg A=" + fraction("AB-x", r"\tg A") + r"\iff x\tg^2 A=AB-x",
        )
        final = fraction("AB", r"1+\tg^2 A")
        numeric = fraction(values["AB"], "1+(" + values["tgA"] + ")^2")
    else:
        rows = (
            r"CH=AH\tg A=(AB-x)\tg A",
            r"CH=" + fraction("BH", r"\tg A") + "=" + fraction("x", r"\tg A"),
            r"(AB-x)\tg A=" + fraction("x", r"\tg A") + r"\iff AB\tg^2 A=x(1+\tg^2 A)",
        )
        final = fraction(r"AB\tg^2 A", r"1+\tg^2 A")
        numeric = fraction(
            "(" + values["AB"] + ")(" + values["tgA"] + ")^2",
            "1+(" + values["tgA"] + ")^2",
        )
    return (
        intro
        + body
        + "".join(line(row) for row in rows)
        + line("x=" + final + "=" + numeric + "=" + answer)
    )


def _pythagoras(values, answer):
    return (
        "<p>По определению тангенса:</p>"
        + line(r"\tg A=" + fraction("BC", "AC"))
        + line(r"BC=AC\tg A")
        + "<p>По теореме Пифагора:</p>"
        + line(r"AC^2+BC^2=AB^2\iff AC^2+(AC\tg A)^2=AB^2")
        + line(
            r"AC="
            + fraction("AB", r"\sqrt{1+\tg^2 A}")
            + "="
            + fraction(values["AB"], r"\sqrt{1+(" + values["tgA"] + ")^2}")
            + "="
            + values["AC"]
        )
        + line(
            r"\cos A="
            + fraction("AC", "AB")
            + "="
            + fraction(values["AC"], values["AB"])
            + "="
            + values["cosA"]
        )
        + line(
            r"\cos A="
            + fraction("AH", "AC")
            + r"\iff AH=AC\cos A=("
            + values["AC"]
            + r")\cdot("
            + values["cosA"]
            + ")="
            + values["AH"]
        )
        + line("BH=AB-AH=(" + values["AB"] + ")-(" + values["AH"] + ")=" + answer)
    )


def render(kind, values, answer):
    ah = kind == "hypotenuse_ah_methods"
    answer = answer.replace(",", "{,}")
    bodies = (
        _trigonometry(values, answer, ah),
        _metric_equation(values, answer) if ah else _two_heights(values, answer, ah),
        _two_heights(values, answer, ah) if ah else _pythagoras(values, answer),
    )
    titles = ("Решение", "Альтернативное решение.", "Альтернативное решение.")
    return "".join(
        solution_section(title, body)
        for title, body in zip(titles, bodies, strict=True)
    )
