"""Disambiguate the two chord-height constructions from the whole condition."""

import re

import sympy as sp
from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from .incircle_model import _positive

SOURCE = "7420a6a1-e81a-46a9-81fc-c953dd1ffad5"
INSIDE_SOURCES = (SOURCE, "928f8239-e49d-4447-9f00-d36e87ac4aa6")
DETAIL = "ac7891b6-247a-4853-9107-02031ac6651d"
CONDITION_KEY = "circumcircle_trapezoid_height_condition"
DETAIL_KEY = "circumcircle_trapezoid_height_detail"
PATTERN = r"Основания равнобедренной трапеции равны\s+(.+?)\s+и\s+(.+?)\s*\.\s*Радиус описанной окружности равен\s+(.+?)\s*\.(?:\s*Центр окружности лежит (внутри|вне) трапеции\s*\.)?\s*Найдите высоту трапеции\s*\."


def condition_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for image in soup.find_all("img"):
        if image.get("data-asset-key") == CONDITION_KEY:
            image["data-asset-key"] = "image_1"
            image["data-transformation-target-id"] = "asset:image_1"
    return str(soup)


def read(text, source):
    match = re.fullmatch(PATTERN, text)
    if match is None:
        return None
    a, b, radius = (_positive(v) for v in match.groups()[:3])
    large, small = max(a, b), min(a, b)
    if large >= 2 * radius or large == small:
        raise ContentPlanError("distinct bases shorter than the diameter are required")
    location = match[4]
    if location is None:
        if source not in INSIDE_SOURCES:
            raise ContentPlanError(
                "the circumcenter location needs textual or reviewed condition-diagram evidence"
            )
        location = "внутри"
    inside = sp.S.One if location == "внутри" else sp.S.Zero
    near = sp.sqrt(radius**2 - large**2 / 4)
    far = sp.sqrt(radius**2 - small**2 / 4)
    return (large, small, radius, inside), sp.simplify(
        far + near if inside else far - near
    )
