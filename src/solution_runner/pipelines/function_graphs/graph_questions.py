"""Canonical condition images and complete mathematical text for graph rules."""

import re

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..triangles.isosceles.planner import _normalized_content, _section


def read(context):
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if not condition:
        raise ContentPlanError("a complete function-graph condition is required")
    soup = BeautifulSoup(condition["html"].replace("\u00ad", ""), "html.parser")
    assets = [a for a in content["assets"] if a.get("asset_key") == "image_1"]
    images = soup.find_all("img")
    if (
        len(assets) != 1
        or len(images) != 1
        or condition.get("asset_keys") != ["image_1"]
        or images[0].get("data-asset-key") != "image_1"
        or images[0].get("data-asset-id") != assets[0].get("asset_id")
        or images[0].get("src") != "/assets/" + str(assets[0].get("asset_id"))
        or soup.select("svg, math, iframe, object")
    ):
        raise ContentPlanError("one canonical audited condition image is required")
    forms = []

    def token(raw):
        forms.append(
            raw.replace(" ", "")
            .replace("−", "-")
            .replace(r"\left", "")
            .replace(r"\right", "")
            .replace(r"\dfrac", r"\frac")
        )
        return " @" + str(len(forms) - 1) + "@ "

    for node in soup.select("[data-inline-latex]"):
        node.replace_with(token(node["data-inline-latex"]))
    text = soup.get_text(" ", strip=True)
    if not forms:
        text = re.sub(r"\$([^$]+)\$", lambda m: token(m[1]), text)
    return forms, " ".join(text.replace("ё", "е").replace("−", "-").split())
