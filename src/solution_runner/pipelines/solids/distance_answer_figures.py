"""Remove only reviewed answer pictures duplicated exactly in the solution."""

from copy import deepcopy
from dataclasses import replace
from html import escape

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _section
from ..triangles.right.basic_parent import _targeted
from ..word_problems.common import rewrite
from .spatial_distance_sources import DATA


def clean_context(context):
    content = context.get("normalized_content") or {}
    if not isinstance(content, dict) or not isinstance(content.get("sections"), list):
        return context
    if (
        any(not isinstance(s, dict) for s in content["sections"])
        or not isinstance(content.get("assets"), list)
        or any(not isinstance(a, dict) for a in content["assets"])
    ):
        return context
    answer = _section(content, "answer")
    solution = _section(content, "solution")
    if (
        not answer
        or not solution
        or not isinstance(answer.get("html"), str)
        or not isinstance(solution.get("html"), str)
        or "<img" not in answer["html"]
    ):
        return context
    soup = BeautifulSoup(answer["html"], "html.parser")
    images = soup.find_all("img")
    references = BeautifulSoup(solution["html"], "html.parser").find_all("img")
    assets = {a.get("asset_key"): a for a in content.get("assets", [])}
    for image in images:
        key = image.get("data-asset-key")
        asset = assets.get(key, {})
        source = image.get("data-asset-id")
        entry = DATA["figures"].get(source)
        if entry is None or not entry.get("answer_duplicate"):
            return context
        same = [r for r in references if r.get("data-asset-key") == key]
        if (
            len(same) != 1
            or {k: v for k, v in image.attrs.items() if k != "alt"}
            != {k: v for k, v in same[0].attrs.items() if k != "alt"}
            or image.get("alt", "") != same[0].get("alt", "")
            or asset.get("asset_id") != source
            or asset.get("url") != image.get("src")
        ):
            return context
    if answer.get("asset_keys") != [i.get("data-asset-key") for i in images]:
        return context
    for image in images:
        image.decompose()
    result = deepcopy(context)
    target = _section(result["normalized_content"], "answer")
    target["html"], target["asset_keys"] = str(soup), []
    return result


def repair_answer(plan, context):
    if clean_context(context) is context:
        return plan
    answer = _targeted(_section(context["normalized_content"], "answer"))
    value = escape(plan.answer, quote=True)
    markup = (
        '<p><span data-inline-latex="' + value + '"></span></p>'
        if "\\" in plan.answer
        else '<p><span data-effect="spaced">' + value + "</span></p>"
    )
    change = rewrite(answer, "answer", "Ответ", markup)
    change["value"]["asset_keys"] = []
    return replace(
        plan,
        transformations=tuple(
            t
            for t in plan.transformations
            if not t["transformation_target_id"].startswith("section:answer")
        )
        + (change,),
    )
