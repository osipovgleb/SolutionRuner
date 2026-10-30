"""Read full applied questions through the existing mathematical-markup grammar."""

import re
from copy import deepcopy

from bs4 import BeautifulSoup

from ..calculus.common import read as read_calculus
from ..probability.common import UnsupportedCondition
from ..triangles.isosceles.planner import _normalized_content, _section


def read(context):
    prepared = deepcopy(context)
    content = _normalized_content(prepared)
    condition = _section(content, "condition")
    if not condition:
        raise UnsupportedCondition("a normalized condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    for tag in soup.find_all("var"):
        if (
            set(tag.attrs) != {"data-math-identifier"}
            or tag.get_text() != tag["data-math-identifier"]
            or not re.fullmatch(r"[a-zA-Zα-ωΑ-Ω]", tag.get_text())
        ):
            raise UnsupportedCondition("one unambiguous physical variable is required")
        tag.unwrap()
    for tag in soup.find_all("sub"):
        index = tag.get_text()
        previous = tag.previous_sibling
        previous_text = (
            previous.get_text()
            if hasattr(previous, "get_text")
            else str(previous or "")
        )
        force_index = index in ["A", "А"] and bool(re.search(r"F\s*$", previous_text))
        if (
            tag.attrs
            or tag.find(True)
            or not (re.fullmatch(r"\d", index) or force_index)
        ):
            raise UnsupportedCondition("only plain physical subscripts are supported")
        tag.replace_with("_A" if force_index else "_" + index)
    condition["html"] = str(soup)
    condition, answer, solution, text = read_calculus(prepared)
    text = text.replace("−", "-").replace("–", "-").replace("υ", "v")
    text = re.sub(r"(?<=[А-Яа-я])e|e(?=[А-Яа-я])", "е", text)
    text = re.sub(r"\s*([=()])\s*", r"\1", text)
    text = re.sub(r"([HTv])\s*(?:_\{0\}|_0)", r"\1_0", text)
    text = text.replace(r"\mathrm{м}", "м")
    text = re.sub(r"\s+\^", "^", text)
    text = text.replace(r"^{\circ}", "°").replace(r"\div \mathrm{мин}", "/мин")
    text = re.sub(r"\bt - (время|секунд)", r"t — \1", text)
    return condition, answer, solution, text
