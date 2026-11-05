"""Read complete prism HTML while retaining explicit geometric vertex subscripts."""

import re

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError

LETTERS = str.maketrans({"А": "A", "В": "B", "С": "C", "Д": "D", "Е": "E", "Ф": "F"})


def _inline(soup, tag, value):
    span = soup.new_tag("span")
    span["data-inline-latex"] = value
    tag.replace_with(span)


def text(html, source=None, *, labels="ABCDEF"):
    alphabet = re.escape(labels)
    vertex = rf"[{alphabet}](?:_1)?"
    label_pattern = rf"{vertex}(?:\s*,?\s*{vertex})*"
    if not isinstance(html, str):
        raise ContentPlanError("complete prism condition HTML is required")
    soup = BeautifulSoup(html, "html.parser")
    for sup in list(soup.find_all("sup")):
        previous = sup.previous_sibling
        if (
            sup.attrs
            or sup.find(True)
            or sup.get_text() != "3"
            or not isinstance(previous, str)
            or not previous.rstrip().endswith("см")
        ):
            raise ContentPlanError(
                "only an explicit cubic-centimeter unit superscript is supported"
            )
        sup.replace_with("3")
    for tag in list(soup.find_all("i")):
        if (
            not tag.attrs
            and len(tag.contents) == 1
            and getattr(tag.contents[0], "name", None) == "sub"
        ):
            tag.unwrap()
    for tag in list(soup.find_all("i")):
        if tag.attrs or any(
            t.name != "sub" or t.attrs or t.get_text() != "1" or t.find(True)
            for t in tag.find_all(True)
        ):
            raise ContentPlanError(
                "only explicit geometric italic labels are supported"
            )
        for sub in tag.find_all("sub"):
            sub.replace_with("_1")
        label = tag.get_text().translate(LETTERS)
        if not (
            re.fullmatch(rf"[{alphabet}_1]+", label)
            or re.fullmatch(label_pattern, label)
        ):
            raise ContentPlanError("the prism vertex label needs review")
        _inline(soup, tag, label)
    for tag in list(soup.find_all("var")):
        label = tag.get_text().translate(LETTERS)
        if (
            tag.find(True)
            or set(tag.attrs) != {"data-math-identifier"}
            or tag["data-math-identifier"] != tag.get_text()
            or not re.fullmatch(rf"[{alphabet}]+", label)
        ):
            raise ContentPlanError("the typed prism identifier changed")
        _inline(soup, tag, label)
    for sub in list(soup.find_all("sub")):
        previous = sub.previous_sibling
        while isinstance(previous, str) and not previous.strip():
            previous = previous.previous_sibling
        if (
            sub.attrs
            or sub.find(True)
            or sub.get_text() != "1"
            or not getattr(previous, "attrs", None)
            or set(previous.attrs) != {"data-inline-latex"}
            or not re.fullmatch(label_pattern, previous["data-inline-latex"])
            or not previous["data-inline-latex"].endswith(tuple(labels))
        ):
            raise ContentPlanError(
                "only a canonical adjacent vertex subscript one is supported"
            )
        previous["data-inline-latex"] += "_1"
        sub.decompose()
    try:
        raw = _text(str(soup), source, labels=labels).replace("ё", "е")
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
    raw = (
        raw.replace(r"^{\circ}", "°")
        .replace(r"^\circ", "°")
        .replace(r"\,", " ")
        .replace("_{1}", "_1")
    )
    raw = re.sub(rf"(?<=[{alphabet}1])\s+(?=[{alphabet}])", "", raw)
    return re.sub(r"\s+([.,;:])", r"\1", raw).replace("пло-щадь", "площадь")
