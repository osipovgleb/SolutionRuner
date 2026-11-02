"""Read the original squared-function substitution and its post-derivation figure."""

import re

from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .power_arithmetic import clean


def substitution(forms):
    for f in forms:
        m = re.fullmatch(r"(\d+)\\(sin|cos)\^(?:2|\{2\})x=([ty])", f)
        if m:
            return m[3], S if m[2] == "sin" else C, int(m[1])
    return None


def kind(forms):
    found = substitution(forms)
    if found and any(r"\frac{1}{\log_" in f for f in forms):
        return "base_square", found[0]
    return None


def finite_kind(forms):
    if (
        r"\frac{1}{\log_ab}=\log_ba" in forms
        and any(re.search(r"x\^(?:2|\{2\})", f) for f in forms)
        and any(r"\sin3x" in f and r"\cos(" in f and r"2\sin(" in f for f in forms)
    ):
        if any(re.search(r"(?<![A-Za-z])[tyuzv]=", f) for f in forms):
            raise UnsupportedCondition(
                "the finite-base log method must retain its direct sum-to-product proof"
            )
        return "finite_base", ""
    return None


def review(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    forms = [clean(n["data-inline-latex"]) for n in soup.select("[data-inline-latex]")]
    found = substitution(forms)
    if found is None or not 0 < found[2] <= 100:
        raise UnsupportedCondition(
            "the parent must retain its original squared-function substitution"
        )
    name = found[0]
    if not any(r"\log_" in f and "=1" in f and name in f for f in forms):
        raise UnsupportedCondition(
            "the parent must reduce reciprocal base change to a linear equation"
        )
    return name


def figure_stage(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    images = soup.find_all("img")
    if not images:
        raise UnsupportedCondition(
            "the squared-base parent must retain its original circle"
        )
    part = images[0].find_parent("li")
    if (
        len(images) != 1
        or part is None
        or part.get("data-list-marker") not in ("a)", "а)")
    ):
        raise UnsupportedCondition(
            "the squared-base circle must follow derivation in part a"
        )
    before = []
    for n in part.descendants:
        if n is images[0]:
            break
        if getattr(n, "attrs", {}).get("data-inline-latex"):
            before.append(clean(n["data-inline-latex"]))
    if not before or r"\pm" not in before[-1] or "k" not in before[-1]:
        raise UnsupportedCondition(
            "the original circle must follow complete back-substitution families"
        )
    return "after-steps"
