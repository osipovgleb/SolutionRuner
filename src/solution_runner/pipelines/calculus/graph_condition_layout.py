"""Place the description, question and graph in a consistent reading order."""

import re
from copy import deepcopy
from dataclasses import replace
from html import escape

from bs4 import BeautifulSoup, NavigableString

from ..probability.common import rewrite
from ..triangles.right.basic_parent import _targeted

_QUESTION = re.compile(
    r"(?<=\.)\s*(?=Найдите\b|Определите\b|В какой\b|При каком\b|Сколько\b|В скольких\b|Среди этих точек\b)"
)
_FORMULA = re.compile(
    r"(?<![a-zA-Z])(?:y\s*=\s*)?[fF]\s*['′]?\s*\(\s*x\s*\)"
    r"|[\[(]\s*[−–-]?\d+\s*[;,]\s*[−–-]?\d+\s*[\])]"
)


def _inline(formula):
    return '<span data-inline-latex="' + escape(formula, quote=True) + '"></span>'


def _render_text(text, formulas):
    fragments = re.split(r"(\ue000\d+\ue000)", text)
    output = []
    for fragment in fragments:
        if fragment.startswith("\ue000"):
            output.append(formulas[int(fragment.strip("\ue000"))])
            continue
        offset = 0
        for match in _FORMULA.finditer(fragment):
            output.append(escape(fragment[offset : match.start()]))
            formula = re.sub(r"\s+", "", match[0]).replace("′", "'")
            output.append(_inline(formula.replace("−", "-").replace("–", "-")))
            offset = match.end()
        output.append(escape(fragment[offset:]))
    return "".join(output)


def format_condition(raw, *, image_width=None):
    soup = BeautifulSoup(raw, "html.parser")
    images = soup.find_all("img")
    if len(images) != 1:
        return raw
    image = images[0].extract()
    image.attrs.pop("data-transformation-target-id", None)
    if image_width is not None:
        image["width"] = str(image_width)
        image.attrs.pop("height", None)
    formulas = []
    for span in soup.select("[data-inline-latex], sub"):
        span.attrs.pop("data-transformation-target-id", None)
        span.replace_with(NavigableString(f"\ue000{len(formulas)}\ue000"))
        formulas.append(str(span))
    for block in soup.find_all(["p", "div", "br", "center"]):
        block.insert_before(" ")
        block.insert_after(" ")
    text = soup.get_text().replace("\xad", "")
    text = re.sub(r"[^\S\ue000]+", " ", text).strip(" \t\n")
    text = re.sub(r" +([,.?!])", r"\1", text)
    description = _QUESTION.search(text)
    if description is None:
        return raw
    paragraphs = [
        text[: description.start()].strip(),
        text[description.end() :].strip(),
    ]
    markup = (
        "".join("<p>" + _render_text(p, formulas) + "</p>" for p in paragraphs)
        + "<center>"
        + str(image)
        + "</center>"
    )
    return str(BeautifulSoup(markup, "html.parser"))


def apply_layout(plan, context, *, image_width=None):
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    changes = list(plan.transformations)
    for index, change in enumerate(changes):
        if change["transformation_target_id"].startswith("section:condition"):
            updated = deepcopy(change)
            html = format_condition(updated["value"]["html"], image_width=image_width)
            updated["value"]["html"] = html
            changes[index] = updated
            return replace(plan, condition_html=html, transformations=tuple(changes))
    html = format_condition(condition["html"], image_width=image_width)
    current = BeautifulSoup(condition["html"], "html.parser")
    for tag in current.find_all(True):
        tag.attrs.pop("data-transformation-target-id", None)
    if str(current) != html:
        change = rewrite(
            _targeted(condition), "condition", condition.get("title", "Условие"), html
        )
        change["value"]["asset_keys"] = list(condition["asset_keys"])
        changes.append(change)
    return replace(plan, condition_html=html, transformations=tuple(changes))
