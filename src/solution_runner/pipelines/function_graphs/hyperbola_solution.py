"""Render two geometric methods for shifted hyperbolas."""

from __future__ import annotations

from fractions import Fraction

from ..core.errors import ContentPlanError
from .hyperbola_format import answer_text, formula, latex, row


def horizontal_solution(
    k: Fraction,
    a: Fraction,
    x: Fraction,
    y: Fraction,
    target: Fraction,
    result: Fraction,
    points_image: str = "",
    offset_image: str = "",
    mode: str = "argument",
    second_point=None,
    offset_point=None,
) -> str:
    x2, y2 = second_point or (-2 * a - x, -y)
    ux, uy = offset_point or (x, y)
    if not y or y == y2 or y2 * (x2 + a) != k or uy * (ux + a) != k:
        raise ContentPlanError("horizontal two-point system disagrees with graph")

    def signed(v):
        return ("+" if v >= 0 else "-") + latex(abs(v))

    def coefficient(v):
        return "a" if v == 1 else "-a" if v == -1 else latex(v) + "a"

    def system(*eq):
        return r"\begin{cases}" + r"\\".join(eq) + r"\end{cases}"

    def denominator(v):
        return latex(v) + signed(a)

    function = rf"f(x)=\frac{{{latex(k)}}}{{x{signed(a)}}}"
    systems = [
        system(
            rf"{latex(y)}=\frac{{k}}{{{latex(x)}+a}}",
            rf"{latex(y2)}=\frac{{k}}{{{latex(x2)}+a}}",
        ),
        system(
            "k=" + latex(x * y) + ("+" if y > 0 else "") + coefficient(y),
            "k=" + latex(x2 * y2) + ("+" if y2 > 0 else "") + coefficient(y2),
        ),
        system(
            coefficient(y - y2) + "=" + latex(x2 * y2 - x * y),
            "k=" + latex(x * y) + ("+" if y > 0 else "") + coefficient(y),
        ),
        system("a=" + latex(a), "k=" + latex(k)),
    ]
    decimal = answer_text(result).replace(".", "{,}")
    if mode == "value":
        finish = row(
            rf"f({latex(target)})=\frac{{{latex(k)}}}{{{denominator(target)}}}=\frac{{{latex(k)}}}{{{latex(target + a)}}}={latex(result)}"
            + ("=" + decimal if decimal != latex(result) else "")
        )
    else:
        finish = row(
            rf"\frac{{{latex(k)}}}{{x{signed(a)}}}={latex(target)}"
            + r"\iff "
            + rf"x{signed(a)}=\frac{{{latex(k)}}}{{{latex(target)}}}={latex(k / target)}"
            + r"\iff "
            + rf"x={latex(result)}"
            + ("=" + decimal if decimal != latex(result) else "")
        )
    shift = (
        f"Так как график сдвинут на {formula(latex(abs(a)))} "
        + ("влево" if a > 0 else "вправо")
        + f", {formula('a=' + signed(a))}."
        if a
        else f"Вертикальная асимптота совпадает с осью ординат, {formula('a=0')}."
    )
    quadrants = "первой и третьей" if k > 0 else "второй и четвёртой"
    return (
        points_image
        + f"<p>Возьмём две точки: {formula(rf'A({latex(x)};{latex(y)})')} и "
        f"{formula(rf'B({latex(x2)};{latex(y2)})')}. Подставим их координаты в формулу "
        f"{formula(r'y=\frac{k}{x+a}')}.</p>"
        + row(r"\iff ".join(systems))
        + row(r"\Rightarrow " + function)
        + finish
        + "<p><b>Альтернативное решение</b></p>"
        + offset_image
        + f"<p>{shift}</p>"
        + f"<p>Ветви графика расположены в {quadrants} четвертях относительно асимптот, "
        f"поэтому {formula('k>0' if k > 0 else 'k<0')}.</p>"
        + f"<p>Возьмём точку на {formula(latex(abs(uy)))} "
        + ("выше" if uy > 0 else "ниже")
        + " горизонтальной асимптоты. Красный горизонтальный отрезок показывает отступ от вертикальной асимптоты: "
        + formula(latex(abs(ux + a)))
        + " "
        + ("вправо" if ux + a > 0 else "влево")
        + ". "
        + formula(r"\Rightarrow k=" + signed(k))
        + ".</p>"
        + row(function)
        + finish
    )


def vertical_solution(
    k: Fraction,
    a: Fraction,
    x: Fraction,
    y: Fraction,
    target: Fraction,
    result: Fraction,
    mode: str,
    points_image: str = "",
    offset_image: str = "",
    second_point=None,
    offset_point=None,
) -> str:
    x2, y2 = second_point or (-x, 2 * a - y)
    dx, py = offset_point or (x, y)
    dy = py - a
    if x2 == x or k / x2 + a != y2 or dx * dy != k:
        raise ContentPlanError("two-point system disagrees with graph evidence")

    def signed(v):
        return ("+" if v >= 0 else "-") + latex(abs(v))

    def coefficient(v):
        if v == 1:
            return "a"
        if v == -1:
            return "-a"
        return latex(v) + "a"

    def system(*equations):
        return r"\begin{cases}" + r"\\".join(equations) + r"\end{cases}"

    function = rf"f(x)=\frac{{{latex(k)}}}{{x}}" + signed(a)
    decimal = answer_text(result).replace(".", "{,}")
    if mode == "value":
        reduced = latex(k / target)
        exact = latex(result)
        calculation = (
            rf"f({latex(target)})=\frac{{{latex(k)}}}{{{latex(target)}}}"
            + signed(a)
            + "="
            + reduced
            + signed(a)
            + "="
            + exact
        )
        if decimal != exact:
            calculation += "=" + decimal
        finish = row(calculation)
    else:
        finish = row(
            rf"\frac{{{latex(k)}}}{{x}}"
            + signed(a)
            + "="
            + latex(target)
            + r"\iff "
            + rf"\frac{{{latex(k)}}}{{x}}={latex(target - a)}"
            + r"\iff "
            + rf"x=\frac{{{latex(k)}}}{{{latex(target - a)}}}={latex(result)}"
            + ("=" + decimal if decimal != latex(result) else "")
        )
    systems = [
        system(
            rf"{latex(y)}=\frac{{k}}{{{latex(x)}}}+a",
            rf"{latex(y2)}=\frac{{k}}{{{latex(x2)}}}+a",
        ),
        system(
            latex(x * y) + "=k" + ("+" if x > 0 else "") + coefficient(x),
            latex(x2 * y2) + "=k" + ("+" if x2 > 0 else "") + coefficient(x2),
        ),
        system(
            latex(x * y - x2 * y2) + "=" + coefficient(x - x2),
            latex(x2 * y2) + "=k" + ("+" if x2 > 0 else "") + coefficient(x2),
        ),
        system("a=" + latex(a), "k=" + latex(k)),
    ]
    chain = r"\iff ".join(systems)
    shift = (
        f"Так как график сдвинут на {formula(latex(abs(a)))} "
        f"{'вверх' if a > 0 else 'вниз'}, {formula('a=' + signed(a))}."
        if a
        else f"Горизонтальная асимптота совпадает с осью абсцисс, {formula('a=0')}."
    )
    quadrants = "первой и третьей" if k > 0 else "второй и четвёртой"
    return (
        points_image
        + f"<p>Возьмём на графике две точки: {formula(rf'A({latex(x)};{latex(y)})')} и "
        f"{formula(rf'B({latex(x2)};{latex(y2)})')}. Подставим их координаты в формулу "
        f"{formula(r'y=\frac{k}{x}+a')}.</p>"
        + row(chain)
        + row(r"\Rightarrow " + function)
        + finish
        + "<p><b>Альтернативное решение</b></p>"
        + offset_image
        + f"<p>{shift}</p>"
        + f"<p>Ветви графика расположены в {quadrants} четвертях относительно асимптот, "
        f"поэтому {formula('k>0' if k > 0 else 'k<0')}.</p>"
        + f"<p>Возьмём точку на {formula(latex(abs(dy)))} "
        f"{'выше' if dy > 0 else 'ниже'} горизонтальной асимптоты. "
        f"Красный горизонтальный отрезок показывает отступ от оси ординат: "
        f"{formula(latex(abs(dx)))} {'вправо' if dx > 0 else 'влево'}. "
        f"{formula(r'\Rightarrow k=' + signed(k))}.</p>" + row(function) + finish
    )


def shift_description(a: Fraction, *, horizontal: bool) -> str:
    base = formula(r"y=rac{k}{x}")
    if not a:
        return f"График {base} не сдвинут, его асимптоты совпадают с осями координат."
    direction = (
        ("влево" if a > 0 else "вправо")
        if horizontal
        else ("вверх" if a > 0 else "вниз")
    )
    return f"График {base} сдвинут на {formula(latex(abs(a)))} по {'горизонтали' if horizontal else 'вертикали'} {direction}."


def offset_description(dx: Fraction, dy: Fraction) -> str:
    return (
        f"Красный горизонтальный отрезок показывает отступ {formula(latex(abs(dx)))} от вертикальной асимптоты "
        f"{'вправо' if dx > 0 else 'влево'}, поэтому {formula('X=' + latex(dx))}. "
        f"От горизонтальной асимптоты точка отстоит на {formula(latex(abs(dy)))} "
        f"{'вверх' if dy > 0 else 'вниз'}, поэтому {formula('Y=' + latex(dy))}."
    )
