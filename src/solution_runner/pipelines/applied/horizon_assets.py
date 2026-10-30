"""Exact reuse of the parent's separate conductor example about mixed units."""

from copy import deepcopy

from bs4 import BeautifulSoup

from ..probability import solution_diagrams as diagrams
from ..probability.common import UnsupportedCondition
from ..triangles.isosceles.planner import _normalized_content, _section
from . import common

ASSET_ID = "cffb1ebf-7c5e-4278-8a51-4fff15662e50"
ALT = "Отдельный пример согласования единиц: медный провод длиной 100 м и сечением 2 мм² имеет сопротивление 0,85 Ом"


def read(context):
    content = _normalized_content(context)
    assets = content.get("assets", [])
    if not assets:
        return common.read(context)
    if len(assets) != 1 or assets[0].get("asset_id") != ASSET_ID:
        raise UnsupportedCondition("only the audited horizon unit example is supported")
    key = assets[0].get("asset_key")
    if (
        not isinstance(key, str)
        or not key
        or assets[0].get("url") not in [None, "/assets/" + ASSET_ID]
    ):
        raise UnsupportedCondition("the unit example needs its exact key and asset URL")
    original_solution = _section(content, "solution")
    clean = deepcopy(context)
    prepared = _normalized_content(clean)
    for section in prepared["sections"]:
        if section.get("asset_keys") and (
            section.get("key") != "solution" or section["asset_keys"] != [key]
        ):
            raise UnsupportedCondition(
                "the unit example must belong only to the solution"
            )
        soup = BeautifulSoup(section.get("html", ""), "html.parser")
        for img in soup.find_all("img"):
            if (
                section.get("key") != "solution"
                or img.get("data-asset-id") != ASSET_ID
                or img.get("data-asset-key") != key
                or img.get("src") not in [None, "/assets/" + ASSET_ID]
            ):
                raise UnsupportedCondition(
                    "the visible unit example must match its attachment"
                )
            img.decompose()
        section["html"] = str(soup)
        section["asset_keys"] = []
    prepared["assets"] = []
    condition, answer, _, text = common.read(clean)
    return condition, answer, original_solution, text


def image(context):
    return diagrams.image(
        _normalized_content(context), "horizon_unit_example", ALT, source_id=ASSET_ID
    )


def required_asset():
    return ({"source_asset_id": ASSET_ID, "section_id": "solution:1", "alt_text": ALT},)
