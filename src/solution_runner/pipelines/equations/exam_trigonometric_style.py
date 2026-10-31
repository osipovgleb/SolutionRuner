"""Read the parent's trigonometric notation, figure placement and selection method."""

import re

from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, T, U


def parent_style(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    text = " ".join(soup.get_text(" ", strip=True).replace("\xad", "").lower().split())
    images = soup.find_all("img")
    selection_method = (
        "circle"
        if "окружност" in text
        or (len(images) == 1 and "на указанном промежутке лежат точки" in text)
        or (len(images) == 1 and "среди представленных корней отберём" in text)
        or (len(images) == 1 and "изображается жирной дугой" in text)
        or (len(images) == 1 and "удовлетворяют числа" in text)
        or (len(images) == 1 and "принадлежат корни" in text and "см." in text)
        or (len(images) == 1 and "отрезку" in text and "принадлежат корни" in text)
        or (len(images) == 1 and "получим точку" in text)
        else "number_line"
        if len(images) == 1 and ("числовой оси" in text or "числовой прямой" in text)
        else "inequalities"
        if "решим неравенства" in text
        or "решив неравенство" in text
        or "двойного неравенства" in text
        or "двойных неравенств" in text
        or "двойное неравенство" in text
        else "progressions"
        if "разность между соседними членами" in text
        else None
    )
    if selection_method is None or any(
        s in text for s in ("другое решение", "еще одно решение", "ещё одно решение")
    ):
        raise UnsupportedCondition("one reviewed interval selection method is required")
    formulas = [
        "".join(s["data-inline-latex"].split())
        for s in soup.select("[data-inline-latex]")
    ]
    from .exam_trigonometric_methods import preference

    function, _ = preference(parent_html)
    if len(images) != (1 if selection_method in ("circle", "number_line") else 0):
        raise UnsupportedCondition(
            "the parent must identify its trigonometric function and one circle"
        )
    position = "none"
    if images:
        image = images[0]
        part = image.find_parent("li")
        position = (
            "outside"
            if part is None
            else "after-intro"
            if any(str(n).strip() for n in image.previous_siblings)
            else "before-intro"
        )
    substitutions = [
        m
        for f in formulas
        for m in re.findall(
            r"(?:([ty])=(?:\\(?:sin|cos|tg|ctg)x|\\frac\{1\}\{\\(?:sin|cos)x\})|\\(?:sin|cos|tg|ctg)x=([ty]))",
            f,
        )
    ]
    substitution = next((left or right for left, right in substitutions), None)
    return (
        {"sin": S, "cos": C, "tg": T, "ctg": U}[function],
        ("полный квадрат" in text),
        any(re.search(r"\(-\d+\)\^\{?k", f) for f in formulas),
        position,
        substitution,
        selection_method,
    )


def division(parent_html):
    text = (
        BeautifulSoup(parent_html, "html.parser")
        .get_text(" ", strip=True)
        .replace("\xad", "")
        .lower()
    )
    return "разделим обе части уравнения на" in text


def homogeneous_method(parent_html):
    text = " ".join(
        BeautifulSoup(parent_html, "html.parser")
        .get_text(" ", strip=True)
        .replace("\xad", "")
        .lower()
        .split()
    )
    return "однородн" in text or "относительно тангенса" in text


def cotangent_method(parent_html):
    formulas = [
        s["data-inline-latex"]
        for s in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]")
    ]
    ratios = [
        name
        for formula in formulas
        for name in re.findall(r"\\(tg|ctg)(?:\d*)x=", "".join(formula.split()))
    ]
    return bool(ratios) and ratios[-1] == "ctg"


def zero_square_method(parent_html):
    formulas = [
        "".join(s["data-inline-latex"].split())
        for s in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]")
    ]
    return any(re.search(r"\\(?:sin|cos)\^\{?2\}?x(?:\\cdot)?\(", f) for f in formulas)


def grouping_method(parent_html):
    formulas = [
        "".join(s["data-inline-latex"].split())
        for s in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]")
    ]
    return any(
        re.search(r"\\(?:sin|cos|tg|ctg)\^\{?2\}?x\([^()]+\)[+-]", f) for f in formulas
    )
