"""Preserve the audited general PDF reference without treating it as task data."""

from copy import deepcopy
from html import escape

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section
from . import math_common
from .common import UnsupportedCondition

PDF = "897a275c-8614-4b7d-9ef0-902806ced49c"
URL = "https://reshuege.ru/doc/math/gushchin_dd-finmatematika.pdf"


def read(context):
    content = _normalized_content(context)
    assets = content.get("assets", [])
    if len(assets) > 1 or any(
        a.get("asset_id") != PDF
        or a.get("kind") != "attachment"
        or a.get("asset_key") != "attachment_1"
        or a.get("url") != "/assets/" + PDF
        for a in assets
    ):
        raise UnsupportedCondition(
            "only the audited general financial-mathematics attachment is supported"
        )
    for s in content["sections"]:
        if s.get("key") != "solution" and s.get("asset_keys"):
            raise UnsupportedCondition(
                "the general PDF may only be referenced by the solution"
            )
        if s.get("key") == "solution":
            if set(s.get("asset_keys", [])) - {"attachment_1"} or (
                s.get("asset_keys") and not assets
            ):
                raise UnsupportedCondition("unknown solution attachment reference")
            for node in BeautifulSoup(s.get("html", ""), "html.parser").select(
                "img, [data-asset-key], [data-asset-id]"
            ):
                if (
                    not assets
                    or node.get("data-asset-id") != PDF
                    or node.get("data-asset-key") != "attachment_1"
                    or (node.get("src") or node.get("href")) != "/assets/" + PDF
                ):
                    raise UnsupportedCondition(
                        "every solution asset reference must point to the audited general PDF"
                    )
    prepared = deepcopy(context)
    prepared["normalized_content"]["assets"] = []
    for s in prepared["normalized_content"]["sections"]:
        if s.get("key") == "solution":
            s["asset_keys"] = []
    text = math_common.read(prepared)[3]
    return (
        content,
        tuple(_section(content, k) for k in ("condition", "answer", "solution")),
        text,
    )


def reference(content):
    asset = next(iter(content.get("assets", [])), None)
    attrs = ""
    if asset:
        url = asset["url"]
        attrs = f' data-asset-id="{PDF}" data-asset-key="attachment_1"'
        keys = ("attachment_1",)
    else:
        url = URL
        keys = ()
    link = f'<a{attrs} href="{escape(url, quote=True)}" rel="noreferrer noopener" target="_blank">«Встречи с финансовой математикой»</a>'
    return (
        "<p>Подробнее о дифференцированных платежах см. статью Д. Д. Гущина "
        + link
        + ".</p>",
        keys,
    )
