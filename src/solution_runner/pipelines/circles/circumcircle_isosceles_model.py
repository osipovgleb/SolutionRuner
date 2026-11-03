"""Exact circumradius and the circumcenter's position for an isosceles triangle."""

import re

import sympy as sp
from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from .incircle_model import _positive

SOURCE = "2dfa5269-0fd0-4665-b051-344e4bf91281"
OBTUSE = "3607b526-1d2a-4e3b-a75d-fbcf5e3daf27"
DETAIL = "8dc1610b-629d-4fb5-9957-7899ce7ed6b0"
CONDITION_KEY = "circumcircle_isosceles_condition"
DETAIL_KEY = "circumcircle_isosceles_detail"
PATTERN = r"Боковые стороны равнобедренного треугольника равны\s+(.+?)\s*,\s*основание равно\s+(.+?)\s*\.\s*Найдите радиус (?:описанной окружности этого треугольника|описанной около этого треугольника окружности)\s*\."


def condition_html(html):
    if CONDITION_KEY not in html:
        return html
    soup = BeautifulSoup(html, "html.parser")
    for image in soup.find_all("img"):
        if image.get("data-asset-key") == CONDITION_KEY:
            image["data-asset-key"] = "image_1"
            image["data-transformation-target-id"] = "asset:image_1"
    return str(soup)


def read(text):
    match = re.fullmatch(PATTERN, text)
    if match is None:
        return None
    leg, base = (_positive(v) for v in match.groups())
    if base >= 2 * leg:
        raise ContentPlanError("the isosceles base must be shorter than the two legs")
    height = sp.sqrt(leg**2 - base**2 / 4)
    return (leg, base), sp.simplify(leg**2 / (2 * height))


def kind(model):
    leg, base = model.given
    difference = sp.simplify(2 * leg**2 - base**2)
    return "right" if difference == 0 else "acute" if difference > 0 else "obtuse"
