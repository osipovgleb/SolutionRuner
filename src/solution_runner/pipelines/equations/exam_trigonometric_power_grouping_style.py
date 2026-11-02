"""Certify the parent's whole grouping and retain its substitution and branch order."""

import re
from dataclasses import replace

from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_power_grouping import polynomial_for, terms
from .exam_trigonometric_power_polynomial import source
from .power_arithmetic import clean


def candidate(html):
    return any(
        re.search(
            r"\)\s*(?:\\cdot\s*)?\(",
            n["data-inline-latex"].replace(r"\left", "").replace(r"\right", ""),
        )
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    )


def pieces(html):
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        text = node["data-inline-latex"]
        if len(text) > 3000:
            raise UnsupportedCondition("a bounded parent power derivation is required")
        for piece in re.split(r"\\(?:iff|Leftrightarrow)|\\\\", text):
            for token in (
                r"\left[",
                r"\right.",
                r"\begin{cases}",
                r"\end{cases}",
                r"\begin{aligned}",
                r"\end{aligned}",
                "&",
            ):
                piece = piece.replace(token, "")
            piece = re.split(r"\\quad", piece)[0].rstrip("., ")
            if r"\log" not in piece:
                yield clean(piece)


def substitution(forms, argument):
    result = None
    for form in forms:
        match = re.match(r"^([tyuzv])=", form)
        if match is None or not any(
            t in form[2:] for t in (r"\sin", r"\cos", r"\tg", r"\ctg")
        ):
            continue
        value, poles, _, domain, wrapper, _ = source(form[2:] + "=0")
        if poles or domain is not None or wrapper is not None:
            raise UnsupportedCondition(
                "the parent substitution must have no additional domain"
            )
        if value != argument or result is not None:
            raise UnsupportedCondition(
                "one substitution of the complete original argument required"
            )
        result = match[1]
    used = set(re.findall(r"(?<![A-Za-z])([tyuzv])(?![A-Za-z])", " ".join(forms)))
    if used - ({result} if result else set()):
        raise UnsupportedCondition(
            "every parent substitution must be read and validated"
        )
    return result


def grouping_figure(html, name):
    if name is None:
        return False
    images = BeautifulSoup(html, "html.parser").find_all("img")
    if len(images) != 1:
        return False
    image = images[0]
    part = image.find_parent("li")
    if part is None or part.get("data-list-marker") not in ("а)", "a)"):
        return False
    before, after = [], []
    seen = False
    for node in part.descendants:
        if node is image:
            seen = True
        elif getattr(node, "attrs", {}).get("data-inline-latex"):
            (after if seen else before).append(node)
    return bool(
        before
        and after
        and candidate("".join(map(str, before)))
        and any(r"\log" in n["data-inline-latex"] for n in after)
    )


def review(data, html):
    text = BeautifulSoup(html, "html.parser").get_text(" ").replace("\xad", "").lower()
    if any(
        s in text
        for s in ("другое решение", "ещё одно решение", "еще одно решение", "случа")
    ):
        raise UnsupportedCondition(
            "another parent method needs a separate grouping review"
        )
    forms = tuple(pieces(html))
    name = substitution(forms, data.argument)
    expected = (data.polynomial, data.univariate, data.mixed)
    found, order, reverse_mixed = set(), [], False
    for form in forms:
        if name:
            form = re.sub(r"\^" + name + r"\b", "^{" + name + "}", form)
            form = re.sub(
                r"(?<![A-Za-z])" + name + r"(?![A-Za-z])",
                lambda m: "(" + data.argument_text + ")",
                form,
            )
        if form.count("=") != 1 or any(
            s in form for s in (r"\gt", r"\lt", r"\in", ">", "<")
        ):
            continue
        try:
            expression, poles, _, domain, wrapper, _ = source(form)
            if poles or domain is not None or wrapper is not None:
                continue
            polynomial, _, coefficient = polynomial_for(
                terms(expression, data.argument), data.bases
            )
        except UnsupportedCondition:
            continue
        if polynomial not in expected:
            raise UnsupportedCondition(
                "a parent power step differs from the complete computed grouping"
            )
        found.add(polynomial)
        if polynomial != data.polynomial and polynomial not in order:
            order.append(polynomial)
            if polynomial == data.mixed:
                reverse_mixed = coefficient < 0
    if found != set(expected) or len(order) != 2:
        raise UnsupportedCondition(
            "the parent must retain the whole grouping and both complete branches"
        )
    return replace(
        data,
        substitution=name,
        order=tuple(order),
        figure_after_grouping=grouping_figure(html, name),
        reverse_mixed=reverse_mixed,
        ratio=1 / data.ratio if reverse_mixed else data.ratio,
    )
