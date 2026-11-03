"""Render reviewed right-triangle methods from exact inferred quantities."""

from ...probability.common import line
from ...word_problems.math_common import fraction as frac
from .altitude_methods import solution_section


def _cosine(v):
    return line(r"\cos A=\sqrt{1-\sin^2 A}=\sqrt{1-(" + v["sinA"] + ")^2}=" + v["cosA"])


def _side(requested, v, answer):
    if requested == "AB":
        return line(
            "AB="
            + frac("AC", r"\cos A")
            + "="
            + frac(v["AC"], v["cosA"])
            + "="
            + answer
        )
    return line(r"AC=AB\cos A=(" + v["AB"] + r")\cdot(" + v["cosA"] + ")=" + answer)


def _sine_hypotenuse(solved, v, answer):
    target = solved.requested
    numerical_ratio = frac(v["AC"], "AB") if target == "AB" else frac("AC", v["AB"])
    first = (
        "<p>Найдём косинус угла A:</p>"
        + _cosine(v)
        + "<p>Следовательно:</p>"
        + _side(target, v, answer)
        + "<p><b>Примечание.</b> Можно воспользоваться определением косинуса:</p>"
        + line(r"\cos A=" + v["cosA"] + "=" + frac("AC", "AB"))
        + line(v["cosA"] + "=" + numerical_ratio)
        + _side(target, v, answer)
    )
    second = (
        "<p>Пусть искомая длина "
        + target
        + " равна x, где x &gt; 0. По определению синуса:</p>"
        + line(target + "=x")
        + line(r"\sin A=" + frac("CB", "AB") + "=" + v["sinA"])
    )
    if target == "AB":
        second += (
            line(frac("CB", "x") + "=" + v["sinA"])
            + line("CB=(" + v["sinA"] + ")x")
            + "<p>Применим теорему Пифагора:</p>"
            + line(r"x^2=(" + v["AC"] + ")^2+((" + v["sinA"] + ")x)^2")
            + line(r"(1-\sin^2 A)x^2=AC^2")
            + "<p>Длина положительна, поэтому:</p>"
            + line(
                "x="
                + frac("AC", r"\sqrt{1-\sin^2 A}")
                + "="
                + frac(v["AC"], r"\sqrt{1-(" + v["sinA"] + ")^2}")
                + "="
                + answer
            )
        )
    else:
        second += (
            line(r"CB=AB\sin A=(" + v["AB"] + r")\cdot(" + v["sinA"] + ")=" + v["BC"])
            + "<p>По теореме Пифагора:</p>"
            + line(r"x^2+CB^2=AB^2")
            + "<p>Берём положительный корень, поскольку x &gt; 0:</p>"
            + line(
                r"x=\sqrt{AB^2-CB^2}=\sqrt{("
                + v["AB"]
                + ")^2-("
                + v["BC"]
                + ")^2}="
                + answer
            )
        )
    return first, second


def _sine_opposite(_solved, v, answer):
    first = "<p>Имеем:</p>" + line(
        r"BC=AC\tg A="
        + frac(r"AC\sin A", r"\sqrt{1-\sin^2 A}")
        + "="
        + frac(
            "(" + v["AC"] + r")\cdot(" + v["sinA"] + ")",
            r"\sqrt{1-(" + v["sinA"] + ")^2}",
        )
        + "="
        + answer
    )
    second = (
        "<p>Найдём косинус угла A:</p>"
        + _cosine(v)
        + "<p>Найдём гипотенузу:</p>"
        + _side("AB", v, v["AB"])
        + "<p>По теореме Пифагора:</p>"
        + line(
            r"BC=\sqrt{AB^2-AC^2}=\sqrt{("
            + v["AB"]
            + ")^2-("
            + v["AC"]
            + ")^2}="
            + answer
        )
    )
    return first, second


def _cosine_hypotenuse(_solved, v, answer):
    body = (
        "<p>По определению косинуса:</p>"
        + line(r"\cos A=" + frac("AC", "AB") + "=" + v["cosA"])
        + line(frac(v["AC"], "AB") + "=" + v["cosA"])
        + line("AB=" + frac(v["AC"], v["cosA"]) + "=" + answer)
        + "<p><b>Примечание.</b> Можно сразу выразить гипотенузу:</p>"
        + _side("AB", v, answer)
    )
    return (body,)


def _inverse_tangent(v, answer):
    return (
        "<p>Пусть AC = x, где x &gt; 0. По определению тангенса:</p>"
        + line("AC=x")
        + line(r"\tg A=" + frac("BC", "AC"))
        + line(r"BC=x\tg A")
        + "<p>По теореме Пифагора:</p>"
        + line(r"AB^2=AC^2+BC^2=x^2+(x\tg A)^2")
        + "<p>Берём положительный корень:</p>"
        + line(
            "x="
            + frac("AB", r"\sqrt{1+\tg^2 A}")
            + "="
            + frac(v["AB"], r"\sqrt{1+(" + v["tgA"] + ")^2}")
            + "="
            + answer
        )
    )


def _tangent_hypotenuse(solved, v, answer):
    if solved.requested == "AC":
        return (_inverse_tangent(v, answer),)
    return (
        "<p>По определению тангенса:</p>"
        + line(r"\tg A=" + frac("BC", "AC"))
        + "<p>Найдём BC:</p>"
        + line(r"BC=AC\cdot\tg A=(" + v["AC"] + r")\cdot(" + v["tgA"] + ")=" + v["BC"])
        + "<p>По теореме Пифагора найдём AB:</p>"
        + line(
            r"AB=\sqrt{AC^2+BC^2}=\sqrt{("
            + v["AC"]
            + ")^2+("
            + v["BC"]
            + ")^2}="
            + answer
        ),
    )


def _tangent_opposite(_solved, v, answer):
    return (
        "<p>По определению тангенса:</p>"
        + line(r"BC=AC\tg A=(" + v["AC"] + r")\cdot(" + v["tgA"] + ")=" + answer),
    )


def _sine_from_opposite(_solved, v, answer):
    return (
        "<p>По определению синуса:</p>"
        + line(
            "AB="
            + frac("BC", r"\sin A")
            + "="
            + frac(v["BC"], v["sinA"])
            + "="
            + answer
        ),
    )


def _cosine_adjacent(_solved, v, answer):
    return (
        "<p>Имеем:</p>"
        + line(
            "AC="
            + frac("BC", r"\tg A")
            + "="
            + frac(r"BC\cos A", r"\sin A")
            + "="
            + frac(r"BC\cos A", r"\sqrt{1-\cos^2 A}")
            + "="
            + frac(
                "(" + v["BC"] + r")\cdot(" + v["cosA"] + ")",
                r"\sqrt{1-(" + v["cosA"] + ")^2}",
            )
            + "="
            + answer
        ),
    )


def _tangent_adjacent(solved, v, answer):
    if "AB" in {k for k, _, _ in solved.givens}:
        return (_inverse_tangent(v, answer),)
    return (
        "<p>По определению тангенса:</p>"
        + line(
            "AC=" + frac("BC", r"\tg A") + "=" + frac(v["BC"], v["tgA"]) + "=" + answer
        ),
    )


def _sine_from_legs(_solved, v, answer):
    return (
        "<p>По определению синуса и теореме Пифагора:</p>"
        + line(
            r"\sin A="
            + frac("BC", "AB")
            + "="
            + frac("BC", r"\sqrt{BC^2+AC^2}")
            + "="
            + frac(v["BC"], r"\sqrt{(" + v["BC"] + ")^2+(" + v["AC"] + ")^2}")
            + "="
            + answer
        ),
    )


_RENDERERS = {
    "sine_hypotenuse": _sine_hypotenuse,
    "sine_opposite": _sine_opposite,
    "cosine_hypotenuse": _cosine_hypotenuse,
    "tangent_hypotenuse": _tangent_hypotenuse,
    "tangent_opposite": _tangent_opposite,
    "sine_from_opposite": _sine_from_opposite,
    "cosine_adjacent": _cosine_adjacent,
    "tangent_adjacent": _tangent_adjacent,
    "sine_from_legs": _sine_from_legs,
}
_TITLES = {
    "sine_hypotenuse": ("Решение", "Приведём другое решение"),
    "sine_opposite": ("Решение", "Альтернативное решение."),
    "tangent_hypotenuse": ("Приведем другое решение:",),
}


def render(kind, solved, values, answer):
    bodies = _RENDERERS[kind](solved, values, answer.replace(",", "{,}"))
    titles = _TITLES.get(kind, ("Решение",))
    return "".join(
        solution_section(title, body)
        for title, body in zip(titles, bodies, strict=True)
    )
