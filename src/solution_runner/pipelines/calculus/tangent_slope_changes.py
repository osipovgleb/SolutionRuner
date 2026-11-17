"""Prepare condition changes for function-and-tangent graphs."""

import hashlib
from html import escape

from bs4 import BeautifulSoup

from ..probability.common import UnsupportedCondition, rewrite
from ..triangles.right.basic_parent import _targeted


def canonical(x):
    s = BeautifulSoup(x or "", "html.parser")
    for tag in s.find_all(True):
        tag.attrs.pop("data-transformation-target-id", None)
    return str(s)


def condition_changes(condition, asset, svg, converted, generated_solution_assets):
    soup = BeautifulSoup(condition["html"], "html.parser")
    image = soup.find("img")
    extra = []
    if converted:
        digest = hashlib.sha256(svg.encode()).hexdigest()
        prepared = [
            a
            for a in generated_solution_assets
            if a["asset_key"] == asset["asset_key"] and a["sha256"] == digest
        ]
        if len(prepared) != 1:
            raise UnsupportedCondition("the prepared SVG must match this source PNG")
        new = prepared[0]
        image["data-asset-id"] = new["source_asset_id"]
        image["src"] = new["url"]
        image["alt"] = "График функции и касательная"
        image["data-transformation-target-id"] = "asset:" + asset["asset_key"]
        extra.append(
            {
                "transformation_target_id": "asset:" + asset["asset_key"],
                "operation": "rewrite",
                "value": {
                    "asset_key": asset["asset_key"],
                    "asset_id": new["source_asset_id"],
                    "url": new["url"],
                    "kind": "ordinary_image",
                    "alt": image["alt"],
                    "parent_target_id": _targeted(condition)[
                        "transformation_target_id"
                    ],
                    "position": 0,
                    "html": str(image),
                },
            }
        )

    def inline(x):
        return '<span data-inline-latex="' + escape(x, quote=True) + '"></span>'

    condition_html = canonical(
        "<p>На рисунке изображены график функции "
        + inline("y=f(x)")
        + " и касательная к нему в точке с абсциссой "
        + inline("x_0")
        + ".</p><p>Найдите значение производной функции "
        + inline("f(x)")
        + " в точке "
        + inline("x_0")
        + ".</p><center>"
        + str(image)
        + "</center>"
    )
    if canonical(condition["html"]) != condition_html:
        change = rewrite(
            _targeted(condition),
            "condition",
            condition.get("title", "Условие"),
            condition_html,
        )
        change["value"]["asset_keys"] = list(condition["asset_keys"])
        extra.append(change)
    return extra
