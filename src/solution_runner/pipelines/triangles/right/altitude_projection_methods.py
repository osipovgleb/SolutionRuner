"""Reviewed projection proofs using complementary trigonometry or subtraction."""

from ...probability.common import line
from ...word_problems.math_common import fraction
from .altitude_methods import review_sections, solution_section
from .altitude_solver import AltitudeSolveError


def parent(soup):
    first = soup.select_one("[data-inline-latex]")
    if first is None:
        raise AltitudeSolveError("a complete parent method is required")
    formula = "".join(first["data-inline-latex"].split()).replace("^{2}", "^2")
    cosine = r"\sqrt{1-\cos^2A}" in formula
    direct = (
        r"AH=AC\cosA=\frac{BC}{\tgA}\cdot\cosA=\frac{BC\cos^2A}{\sinA}=\frac{BC\cos^2A}{\sqrt{1-\cos^2A}}="
        if cosine
        else r"AH=AC\cosA=\frac{BC}{tgA}\cdot\cosA=\frac{BC\cos^2A}{\sinA}=\frac{BC(1-\sin^2A)}{\sinA}="
    )
    definition = r"\sin\angleA=\frac{BC}{AB}\iffAB=\frac{BC}{\sin\angleA}="
    subtraction = (
        (
            r"\sinA=\sqrt{1-\cos^2A}=",
            r"AB=\frac{BC}{\sinA}=",
            r"HB=BC\cdot\sinA=",
        )
        if cosine
        else (
            definition,
            r"\sin\angleHCB=\frac{HB}{BC}\iffHB=BC\cdot\sin\angleHCB=",
        )
    )
    expected = [("Решение", (direct,)), ("Альтернативное решение.", subtraction)]
    if not cosine:
        expected.append(
            (
                "Альтернативное решение.",
                (
                    definition,
                    r"AC^2=AB^2-BC^2=",
                    r"AC^2=AB\cdotAH\iffAH=\frac{AC^2}{AB}=",
                ),
            )
        )
    review_sections(soup, expected)
    function = "cosA" if cosine else "sinA"
    return (
        "projection_" + function + "_methods",
        "AH",
        {"BC", function},
        False,
        False,
        False,
    )


def _hypotenuse(values):
    return line(
        r"\sin A="
        + fraction("BC", "AB")
        + r"\iff AB="
        + fraction("BC", r"\sin A")
        + "="
        + fraction(values["BC"], values["sinA"])
        + "="
        + values["AB"]
    )


def render(kind, values, answer):
    cosine = kind == "projection_cosA_methods"
    answer = answer.replace(",", "{,}")
    numerator = r"BC\cos^2 A" if cosine else r"BC(1-\sin^2 A)"
    denominator = r"\sqrt{1-\cos^2 A}" if cosine else r"\sin A"
    numeric_top = (
        "(" + values["BC"] + ")(" + values["cosA"] + ")^2"
        if cosine
        else "(" + values["BC"] + ")(1-(" + values["sinA"] + ")^2)"
    )
    numeric_bottom = (
        r"\sqrt{1-(" + values["cosA"] + ")^2}" if cosine else values["sinA"]
    )
    direct = line(
        r"AH=AC\cos A="
        + fraction("BC", r"\tg A")
        + r"\cdot\cos A="
        + fraction(r"BC\cos^2 A", r"\sin A")
        + "="
        + fraction(numerator, denominator)
        + "="
        + fraction(numeric_top, numeric_bottom)
        + "="
        + answer
    )
    complement = (
        line(
            r"\sin A=\sqrt{1-\cos^2 A}=\sqrt{1-("
            + values["cosA"]
            + ")^2}="
            + values["sinA"]
        )
        if cosine
        else ""
    )
    subtraction = (
        complement
        + _hypotenuse(values)
        + (
            "<p>Углы CAB и BCH равны. Из прямоугольного треугольника HCB:</p>"
            + line(
                r"\sin\angle HCB="
                + fraction("HB", "BC")
                + r"\iff HB=BC\sin\angle HCB=("
                + values["BC"]
                + r")\cdot("
                + values["sinA"]
                + ")="
                + values["BH"]
            )
            + line("AH=AB-HB=(" + values["AB"] + ")-(" + values["BH"] + ")=" + answer)
        )
    )
    html = solution_section(
        "Решение", "<p>По определениям косинуса и тангенса:</p>" + direct
    )
    html += solution_section("Альтернативное решение.", subtraction)
    if not cosine:
        html += solution_section("Альтернативное решение.", _metric(values, answer))
    return html


def _metric(values, answer):
    metric = _hypotenuse(values) + (
        "<p>По теореме Пифагора:</p>"
        + line(
            r"AC^2=AB^2-BC^2=("
            + values["AB"]
            + ")^2-("
            + values["BC"]
            + ")^2=("
            + values["AC"]
            + ")^2"
        )
        + "<p>Квадрат катета равен произведению гипотенузы и проекции катета:</p>"
        + line(
            r"AC^2=AB\cdot AH\iff AH="
            + fraction("AC^2", "AB")
            + "="
            + fraction("(" + values["AC"] + ")^2", values["AB"])
            + "="
            + answer
        )
    )
    return metric
