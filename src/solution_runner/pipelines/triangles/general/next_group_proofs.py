"""Render reviewed parent-faithful proofs for general-triangle groups."""

from __future__ import annotations

import re
from collections.abc import Callable
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from ..right.planner import RightTrianglePlanError


def _condition_stream(condition_html: str) -> str:
    """Return visible condition text with inline LaTeX restored in place."""

    soup = BeautifulSoup(condition_html, "html.parser")
    for formula in soup.find_all(attrs={"data-inline-latex": True}):
        formula.replace_with(str(formula.get("data-inline-latex") or ""))
    return " ".join(
        soup.get_text(" ", strip=True)
        .replace("\u00ad", "")
        .replace("\u202f", " ")
        .split()
    )


def _degree_assignment(text: str, name: str) -> int:
    match = re.search(
        rf"угол\s+{re.escape(name)}\s+равен\s*(\d+)\s*(?:\^\{{\\circ\}}|°)",
        text,
        re.IGNORECASE,
    )
    if match is None:
        raise RightTrianglePlanError(f"condition must give angle {name}")
    return int(match.group(1))


def _latex_number(value: Fraction | int) -> str:
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    if value.denominator in {2, 4, 5, 10, 20, 25, 50, 100}:
        return f"{float(value):g}".replace(".", "{,}")
    return rf"\frac{{{value.numerator}}}{{{value.denominator}}}"


def _answer_text(value: Fraction | int) -> str:
    return _latex_number(value).replace("{,}", ",")


def _replace_latex(parent_html: str, formulas: tuple[str, ...]) -> str:
    """Replace every parent formula in order while retaining all other HTML."""

    if not parent_html.strip():
        raise RightTrianglePlanError("registered group parent has no solution")
    matches = list(re.finditer(r'data-inline-latex="[^"]*"', parent_html))
    if len(matches) != len(formulas):
        raise RightTrianglePlanError(
            f"parent solution formula count drifted: {len(matches)} != {len(formulas)}"
        )
    iterator = iter(formulas)
    return re.sub(
        r'data-inline-latex="[^"]*"',
        lambda _match: f'data-inline-latex="{next(iterator)}"',
        parent_html,
    )


def _answer_matches(section: dict[str, Any] | None, expected: Fraction | int) -> bool:
    if section is None:
        return False
    current = BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text(
        " ", strip=True
    )
    try:
        return Fraction(current.replace(",", ".")) == Fraction(expected)
    except (ValueError, ZeroDivisionError):
        return False


def _has_condition_asset(condition: dict[str, Any], asset_id: str) -> bool:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    image = soup.find("img", attrs={"data-asset-key": "image_1"})
    return image is not None and str(image.get("data-asset-id") or "") == asset_id


def _relabeled_midline_solution(parent_html: str, triangle: str) -> str:
    """Relabel the parent's CDE proof for the requested corner triangle."""

    mappings = {
        "CDE": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
        "ADE": {"A": "B", "B": "C", "C": "A", "D": "D", "E": "E"},
        "BDE": {"A": "C", "B": "A", "C": "B", "D": "D", "E": "E"},
    }
    mapping = mappings[triangle]
    if triangle == "CDE":
        return parent_html
    soup = BeautifulSoup(parent_html, "html.parser")
    for variable in soup.find_all("var", attrs={"data-math-identifier": True}):
        old = str(variable.get("data-math-identifier") or "")
        new = "".join(mapping.get(letter, letter) for letter in old)
        if new in {"BCA", "CAB"}:
            new = "ABC"
        variable["data-math-identifier"] = new
        variable.string = new
    for formula in soup.find_all(attrs={"data-inline-latex": True}):
        old = str(formula.get("data-inline-latex") or "")
        new = "".join(mapping.get(char, char) for char in old)
        formula["data-inline-latex"] = new.replace("BCA", "ABC").replace("CAB", "ABC")
    return str(soup)


def _without_image(parent_html: str, asset_key: str) -> str:
    """Remove one parent image and its now-empty wrapper from copied HTML."""

    soup = BeautifulSoup(parent_html, "html.parser")
    for image in list(soup.find_all("img", attrs={"data-asset-key": asset_key})):
        wrapper = image.parent
        image.decompose()
        if (
            wrapper is not None
            and wrapper.name in {"p", "center", "figure"}
            and not wrapper.get_text(strip=True)
            and wrapper.find(("img", "audio", "video")) is None
        ):
            wrapper.decompose()
    return str(soup)


def _build_27768(text: str, parent_html: str) -> tuple[Fraction, str]:
    required = ("AD", "AB", "CD", "биссектриса", "меньший угол")
    if not all(token in text for token in required):
        raise RightTrianglePlanError("condition must state AD bisects A and AB=AD=CD")
    if not parent_html.strip():
        raise RightTrianglePlanError("registered group parent has no solution")
    return Fraction(36), parent_html


def _build_27769(text: str, parent_html: str) -> tuple[Fraction, str]:
    if (
        not all(token in text for token in ("BD", "BC", "BCD"))
        or "продолжении" not in text
    ):
        raise RightTrianglePlanError(
            "condition must state the BD=BC extension construction"
        )
    angle_a = _degree_assignment(text, "A")
    angle_c = _degree_assignment(text, "C")
    angle_b = 180 - angle_a - angle_c
    answer = Fraction(angle_b, 2)
    exterior = angle_a + angle_c
    return answer, (
        '<p>Сумма углов треугольника <var data-math-identifier="ABC">ABC</var> '
        'равна 180°, поэтому</p><center><p><span data-inline-latex="'
        rf"\angle B=180^{{\circ}}-\angle A-\angle C="
        rf"180^{{\circ}}-{angle_a}^{{\circ}}-{angle_c}^{{\circ}}="
        rf"{angle_b}^{{\circ}}"
        '"></span>.</p></center><p>Угол <var data-math-identifier="CBD">CBD</var> '
        'смежный с углом <var data-math-identifier="B">B</var>, поэтому</p>'
        '<center><p><span data-inline-latex="'
        rf"\angle CBD=180^{{\circ}}-\angle B="
        rf"180^{{\circ}}-{angle_b}^{{\circ}}={exterior}^{{\circ}}"
        '"></span>.</p></center><p>Треугольник '
        '<var data-math-identifier="CBD">CBD</var> — равнобедренный, так как '
        '<var data-math-identifier="BD">BD</var> = '
        '<var data-math-identifier="BC">BC</var>.</p><p>Следовательно,</p>'
        '<center><p><span data-inline-latex="'
        rf"\angle D=\frac{{180^{{\circ}}-\angle CBD}}{{2}}="
        rf"\frac{{180^{{\circ}}-{exterior}^{{\circ}}}}{{2}}="
        rf"{_latex_number(answer)}^{{\circ}}"
        '"></span>.</p></center>'
    )


def _build_27776(text: str, parent_html: str) -> tuple[Fraction, str]:
    if not all(token in text for token in ("AD", "AE", "AC", "BDE", "биссектриса")):
        raise RightTrianglePlanError(
            "condition must state the AD and AE=AC construction"
        )
    angle_b = _degree_assignment(text, "B")
    angle_c = _degree_assignment(text, "C")
    answer = Fraction(angle_c - angle_b)
    if answer <= 0:
        raise RightTrianglePlanError("condition gives a non-positive BDE angle")
    angle_deb = 180 - angle_c
    return answer, (
        '<p>Треугольники <var data-math-identifier="CAD">CAD</var> и '
        '<var data-math-identifier="EAD">EAD</var> равны по двум сторонам и '
        'углу между ними, поэтому</p><center><p><span data-inline-latex="'
        rf"\angle C=\angle DEA={angle_c}^{{\circ}}"
        '"></span>.</p></center><p>Углы '
        '<var data-math-identifier="DEA">DEA</var> и '
        '<var data-math-identifier="DEB">DEB</var> смежные, поэтому</p>'
        '<center><p><span data-inline-latex="'
        rf"\angle DEB=180^{{\circ}}-\angle DEA="
        rf"180^{{\circ}}-{angle_c}^{{\circ}}={angle_deb}^{{\circ}}"
        '"></span>.</p></center><p>Сумма углов треугольника '
        '<var data-math-identifier="BDE">BDE</var> равна 180°.</p>'
        '<p>Следовательно,</p><center><p><span data-inline-latex="'
        rf"\angle BDE=180^{{\circ}}-\angle B-\angle DEB="
        rf"180^{{\circ}}-{angle_b}^{{\circ}}-{angle_deb}^{{\circ}}="
        rf"{_latex_number(answer)}^{{\circ}}"
        '"></span>.</p></center>'
    )


def _build_27777(text: str, parent_html: str) -> tuple[Fraction, str]:
    required = ("CD", "внешнего угла", "CE", "CB", "BDE", "биссектриса")
    if not all(token in text for token in required):
        raise RightTrianglePlanError(
            "condition must state the exterior-bisector construction"
        )
    angle_a = _degree_assignment(text, "A")
    angle_b = _degree_assignment(text, "B")
    half_sum = Fraction(angle_a + angle_b, 2)
    cbd = 180 - angle_b
    half_answer = Fraction(180) - half_sum - cbd
    answer = 2 * half_answer
    if answer <= 0:
        raise RightTrianglePlanError("condition gives a non-positive BDE angle")
    rendered = _replace_latex(
        parent_html,
        (
            r"\angle BDC=\angle CDE",
            r"\angle BDE=2\angle BDC=2(180^{\circ}-\angle BCD-\angle CBD)",
            rf"\angle BCD=\frac{{\angle BCE}}{{2}}=\frac{{\angle A+\angle B}}{{2}}={_latex_number(half_sum)}^{{\circ}}",
            rf"\angle CBD=180^{{\circ}}-\angle B={cbd}^{{\circ}}",
            rf"\angle BDE=2(180^{{\circ}}-{_latex_number(half_sum)}^{{\circ}}-{cbd}^{{\circ}})=2\cdot {_latex_number(half_answer)}^{{\circ}}={_latex_number(answer)}^{{\circ}}",
        ),
    )
    soup = BeautifulSoup(rendered, "html.parser")
    formulas = soup.find_all(attrs={"data-inline-latex": True})
    intermediate = formulas[2].find_parent("p") if len(formulas) == 5 else None
    if intermediate is None or formulas[3].find_parent("p") is not intermediate:
        raise RightTrianglePlanError("group 27777 intermediate formula layout drifted")
    intermediate.wrap(soup.new_tag("center"))
    return answer, str(soup)


def _build_27778(text: str, parent_html: str) -> tuple[Fraction, str]:
    if not all(
        token in text for token in ("AD", "BE", "CF", "O", "AOF", "биссектрисы")
    ):
        raise RightTrianglePlanError("condition must state three concurrent bisectors")
    angle_a = _degree_assignment(text, "A")
    angle_b = _degree_assignment(text, "B")
    angle_c = 180 - angle_a - angle_b
    angle_f = Fraction(180 - angle_a) - Fraction(angle_c, 2)
    answer = Fraction(90) - Fraction(angle_b, 2)
    parent = BeautifulSoup(parent_html, "html.parser")
    sections = parent.find_all("section", attrs={"data-content-kind": "solution"})
    if len(sections) != 2:
        raise RightTrianglePlanError(
            "group 27778 parent must contain two solution methods"
        )
    direct = sections[1]
    label = direct.find("b")
    if label is not None and label.find_parent("p") is not None:
        label.find_parent("p").decompose()
    direct_html = "".join(str(item) for item in direct.contents)
    return answer, _replace_latex(
        direct_html,
        (
            rf"\angle C=180^{{\circ}}-\angle A-\angle B=180^{{\circ}}-{angle_a}^{{\circ}}-{angle_b}^{{\circ}}={angle_c}^{{\circ}}",
            rf"\angle F=180^{{\circ}}-\angle A-\angle ACF=180^{{\circ}}-{angle_a}^{{\circ}}-\frac{{{angle_c}^{{\circ}}}}{{2}}={_latex_number(angle_f)}^{{\circ}}",
            rf"\angle AOF=180^{{\circ}}-\angle OAF-\angle F=180^{{\circ}}-\frac{{{angle_a}^{{\circ}}}}{{2}}-{_latex_number(angle_f)}^{{\circ}}={_latex_number(answer)}^{{\circ}}",
        ),
    )


def _build_27779(text: str, parent_html: str) -> tuple[Fraction, str]:
    if not all(token in text for token in ("AD", "BE", "CF", "O", "AOF", "высоты")):
        raise RightTrianglePlanError("condition must state three concurrent altitudes")
    _degree_assignment(text, "A")
    angle_b = _degree_assignment(text, "B")
    answer = Fraction(angle_b)
    return answer, _replace_latex(
        parent_html,
        (rf"\angle AOF=\angle B={angle_b}^{{\circ}}",),
    )


def _build_317337(text: str, parent_html: str) -> tuple[Fraction, str]:
    if "DE" not in text or "средняя линия" not in text or "ABC" not in text:
        raise RightTrianglePlanError(
            "condition must give a triangle area cut by midline DE"
        )
    match = re.search(
        r"Площадь треугольника\s+(ADE|BDE|CDE)\s+равна\s*(\d+)", text, re.IGNORECASE
    )
    if match is None:
        raise RightTrianglePlanError(
            "condition must give exactly one ADE, BDE, or CDE area"
        )
    triangle = match.group(1).upper()
    small_area = int(match.group(2))
    answer = Fraction(4 * small_area)
    if triangle == "CDE":
        rendered = _replace_latex(
            parent_html,
            (
                rf"S_{{ABC}}=2^{{2}}\cdot {small_area}={_latex_number(answer)}",
                rf"S_{{ABC}}=S_{{AEC}}+S_{{CBE}}=S_{{CDE}}+S_{{ADE}}+S_{{CBE}}=4S_{{CDE}}=4\cdot {small_area}={_latex_number(answer)}",
            ),
        )
        return answer, _without_image(rendered, "image_1")
    relabeled = _relabeled_midline_solution(parent_html, triangle)
    soup = BeautifulSoup(relabeled, "html.parser")
    formulas = list(soup.find_all(attrs={"data-inline-latex": True}))
    if len(formulas) != 2:
        raise RightTrianglePlanError(
            "group 317337 parent solution formula count drifted"
        )
    first = str(formulas[0].get("data-inline-latex") or "")
    first = re.sub(
        r"2\^\{2\}\\cdot\s*\d+\s*=\s*\d+",
        lambda _match: rf"2^{{2}}\cdot {small_area}={_latex_number(answer)}",
        first,
    )
    formulas[0]["data-inline-latex"] = first
    second = str(formulas[1].get("data-inline-latex") or "")
    second = re.sub(
        r"4\\cdot\s*\d+\s*=\s*\d+",
        lambda _match: rf"4\cdot {small_area}={_latex_number(answer)}",
        second,
    )
    formulas[1]["data-inline-latex"] = second
    return answer, _without_image(str(soup), "image_1")


def _build_319058(text: str, parent_html: str) -> tuple[Fraction, str]:
    if not all(
        token in text
        for token in ("ABC", "DE", "AB", "средняя линия", "параллельная", "трапеции")
    ):
        raise RightTrianglePlanError(
            "condition must request the midline trapezoid area"
        )
    match = re.search(
        r"Площадь треугольника\s+ABC\s+равна\s*(\d+)", text, re.IGNORECASE
    )
    if match is None:
        raise RightTrianglePlanError("condition must give area ABC")
    total = int(match.group(1))
    small = Fraction(total, 4)
    answer = Fraction(3 * total, 4)
    rendered = _replace_latex(
        parent_html,
        (
            rf"S_{{CDE}}=\frac{{1}}{{4}}\cdot {total}={_latex_number(small)}",
            rf"S_{{\mathrm{{трап}}}}=S_{{ABC}}-S_{{CDE}}={total}-{_latex_number(small)}={_latex_number(answer)}",
        ),
    )
    soup = BeautifulSoup(rendered, "html.parser")
    for image in list(soup.find_all("img")):
        wrapper = image.parent
        image.decompose()
        if (
            wrapper is not None
            and wrapper.name in {"p", "center", "figure"}
            and not wrapper.get_text(strip=True)
            and wrapper.find(("img", "audio", "video")) is None
        ):
            wrapper.decompose()
    return answer, str(soup)


def _build_500142(text: str, parent_html: str) -> tuple[Fraction, str]:
    required = ("BD", "CE", "DOE")
    if not all(token in text for token in required) or "высот" not in text.lower():
        raise RightTrianglePlanError("condition must state the BD and CE altitudes")
    match = re.search(
        r"угол\s+[AА]\s+равен\s*(\d+)\s*"
        r"(?:\^\{\\circ\}|°|градус(?:ам|а|ов)?)",
        text,
        re.IGNORECASE,
    )
    if match is None:
        raise RightTrianglePlanError("condition must give angle A")
    angle_a = int(match.group(1))
    answer = Fraction(180 - angle_a)
    if answer <= 0:
        raise RightTrianglePlanError("condition gives a non-positive DOE angle")
    return answer, _replace_latex(
        parent_html,
        (
            (
                rf"\angle DOE=360^{{\circ}}-\angle ADO-\angle OEA-\angle A="
                rf"360^{{\circ}}-90^{{\circ}}-90^{{\circ}}-{angle_a}^{{\circ}}="
                rf"{_latex_number(answer)}^{{\circ}}"
            ),
        ),
    )


def _build_510796(text: str, parent_html: str) -> tuple[Fraction, str]:
    required = ("BD", "CE", "DOE")
    if (
        not all(token in text for token in required)
        or "продолжения высот" not in text.lower()
    ):
        raise RightTrianglePlanError(
            "condition must state the extended BD and CE altitudes"
        )
    angle_a = _degree_assignment(text, "A")
    answer = Fraction(180 - angle_a)
    if answer <= 0:
        raise RightTrianglePlanError("condition gives a non-positive DOE angle")
    return answer, _replace_latex(
        parent_html,
        (
            (
                rf"\angle DOE=\angle CAE=180^{{\circ}}-\angle CAB="
                rf"180^{{\circ}}-{angle_a}^{{\circ}}={_latex_number(answer)}^{{\circ}}"
            ),
        ),
    )


_BUILDERS: dict[str, Callable[[str, str], tuple[Fraction, str]]] = {
    "general-triangle-27768-bisector-equal-segments-angle": _build_27768,
    "general-triangle-27769-extension-isosceles-angle": _build_27769,
    "general-triangle-27776-bisector-congruent-angle": _build_27776,
    "general-triangle-27777-exterior-bisector-isosceles-angle": _build_27777,
    "general-triangle-27778-incenter-bisectors-angle": _build_27778,
    "general-triangle-27779-orthocenter-altitudes-angle": _build_27779,
    "general-triangle-317337-midline-small-area-to-total": _build_317337,
    "general-triangle-319058-midline-trapezoid-area": _build_319058,
    "general-triangle-500142-altitudes-obtuse-angle": _build_500142,
    "general-triangle-510796-extended-altitudes-angle": _build_510796,
}
