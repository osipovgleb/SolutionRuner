"""Read one complete distance, angle or tangent question with explicit vertex indices."""

import re

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError
from .orthogonal_element_geometry import VERTEX

RIGHT = r"Все двугранные углы (?:многогранника )?прямые\."
SETUP = r"На рисунке изображен многогранник, все двугранные углы (?:многогранника )?прямые\."
DISTANCE = (
    rf"Найдите (расстояние|квадрат расстояния) между вершинами ({VERTEX}) и ({VERTEX})"
)
ANGLE = rf"Найдите (угол|тангенс угла) ((?:{VERTEX}){{3}})"


def _indexed(soup):
    for tag in list(soup.find_all(["var", "i", "em"])):
        if not tag.find("sub"):
            continue
        if tag.name == "var":
            if tag.attrs != {"data-math-identifier": tag.get_text()}:
                raise ContentPlanError("the complete indexed identifier changed")
        elif tag.attrs:
            raise ContentPlanError("unreviewed indexed vertex markup")
        if any(
            n.name != "sub" or n.attrs or n.find(True) or n.get_text() not in "123"
            for n in tag.find_all(True)
        ):
            raise ContentPlanError(
                "only explicit vertex indices one to three are supported"
            )
        for sub in list(tag.find_all("sub")):
            sub.replace_with("_" + sub.get_text())
        label = tag.get_text()
        if re.fullmatch(rf"(?:{VERTEX}){{1,3}}", label) is None:
            raise ContentPlanError("the indexed vertex identifier needs review")
        span = soup.new_tag("span")
        span["data-inline-latex"] = label
        tag.replace_with(span)
    for sub in list(soup.find_all("sub")):
        previous = sub.previous_sibling
        while isinstance(previous, str) and not previous.strip():
            previous = previous.previous_sibling
        if sub.attrs or sub.find(True) or sub.get_text() not in {"1", "2", "3"}:
            raise ContentPlanError("one explicit vertex index is required")
        if getattr(previous, "name", None) not in {"var", "i", "em"}:
            raise ContentPlanError("the index must follow its geometric identifier")
        label = previous.get_text()
        valid = previous.attrs == (
            {"data-math-identifier": label} if previous.name == "var" else {}
        )
        label += "_" + sub.get_text()
        if (
            not valid
            or previous.find(True)
            or re.fullmatch(rf"(?:{VERTEX}){{1,3}}", label) is None
        ):
            raise ContentPlanError("the adjacent indexed identifier needs review")
        span = soup.new_tag("span")
        span["data-inline-latex"] = label
        previous.replace_with(span)
        sub.decompose()


def read(html, source):
    if not isinstance(html, str):
        raise ContentPlanError("one complete orthogonal element condition is required")
    soup = BeautifulSoup(html, "html.parser")
    _indexed(soup)
    try:
        raw = _text(str(soup), source, labels="ABCDEFG").replace("ё", "е")
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
    raw = re.sub(r"([A-G])\s*([123])\b", r"\1_\2", raw)
    raw = re.sub(r"_\{([123])\}", r"_\1", raw)
    raw = re.sub(r"(?<=[A-G123])\s+(?=[A-G])", "", raw)
    raw = re.sub(r"\s+([.,])", r"\1", raw)
    match = re.fullmatch(rf"({SETUP}) (.+)\.", raw)
    if match:
        question = match[2]
    else:
        match = re.fullmatch(
            rf"(.+) многогранника, изображенного на рисунке\. {RIGHT}(?: Ответ дайте в градусах\.)?",
            raw,
        )
        if match is None:
            raise ContentPlanError(
                "one complete reviewed orthogonal element question is required"
            )
        question = match[1]
        if "Ответ дайте в градусах" in raw:
            question += ". Ответ дайте в градусах"
    match = re.fullmatch(DISTANCE, question)
    if match:
        return ("distance" if match[1] == "расстояние" else "distance_squared"), match[
            2
        ] + match[3]
    match = re.fullmatch(ANGLE + r"(?:\. Ответ дайте в градусах)?", question)
    if match and ((match[1] == "угол") == question.endswith("Ответ дайте в градусах")):
        return ("angle" if match[1] == "угол" else "tangent"), match[2]
    raise ContentPlanError("the requested geometric quantity or units need review")
