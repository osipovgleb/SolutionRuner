"""Retain each parent's integer letter only for a certified affine root series."""

import re

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .power_arithmetic import ScalarParser


def root_rights(parent_html):
    for node in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]"):
        text = re.sub(
            r"(\\(?:sin|cos|tg|ctg)(?:\^\{?\d+\}?)?)\s+x",
            r"\1x",
            node["data-inline-latex"],
        )
        for match in re.finditer(r"(?<![A-Za-z0-9])x\s*&?=", text):
            yield (
                re.split(
                    r",|;|\\\\|\\(?:quad|end|iff|Leftrightarrow)",
                    text[match.end() :],
                    maxsplit=1,
                )[0]
                .strip()
                .removesuffix(".")
            )


def affine_families(parent_html):
    result = []
    for right in root_rights(parent_html):
        letters = set(
            re.findall(r"[knl]", re.sub(r"\\[A-Za-z]+", "", right.replace(r"\pi", " ")))
        )
        if len(letters) != 1:
            continue
        letter = next(iter(letters))
        try:
            value = sp.expand(
                ScalarParser(right.replace(r"\pi", "p"), (letter, "p")).parse()
            )
        except UnsupportedCondition:
            continue
        k, p = sp.symbols(letter + " p", real=True)
        offset, period = value.subs(k, 0) / p, value.coeff(k) / p
        if (
            offset.is_Rational is True
            and period.is_Rational is True
            and period > 0
            and sp.expand(value - p * (offset + period * k)) == 0
        ):
            result.append((offset, period, letter))
    return tuple(dict.fromkeys(result))


def single_family(parent_html):
    roots = {"".join(right.split()) for right in root_rights(parent_html)}
    return len(roots) == len(affine_families(parent_html)) == 1


def names(parent_html, series):
    source = affine_families(parent_html)
    result = []
    for offset, period in series:
        matching = {
            letter
            for q, p, letter in source
            if p == period and sp.simplify((offset - q) / period).is_Integer is True
        }
        if len(matching) != 1:
            return ()
        result.append(next(iter(matching)))
    return tuple(result)


def doubled_tangent(parent_html, scale):
    for node in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]"):
        text = "".join(node["data-inline-latex"].split())
        for term in re.split(r"\\(?:iff|Leftrightarrow)", text):
            match = re.fullmatch(r"\\tg(\d+)x&?=[+-]?\d+", term)
            if match and sp.Integer(match[1]) == 2 * scale:
                return True
    return False


def notation(result, parent_html):
    from dataclasses import replace

    from .exam_trigonometric import select

    if result.angle_product is not None and result.angle_product.source_poles:
        from .exam_trigonometric_restricted_families import prepare

        return replace(result, restricted_families=prepare(result, parent_html))
    if result.homogeneous is not None and result.homogeneous.source_poles:
        source = affine_families(parent_html)
        if len(source) == len(result.series) == 1 and names(parent_html, result.series):
            q, p, _ = source[0]
            selected, trace = select(((q, p),), result.bounds)
            result = replace(
                result, series=((q, p),), selected=selected, selections=trace
            )
    parameters = names(parent_html, result.series)
    return replace(
        result,
        family_parameters=parameters
        if len(set(parameters)) > 1 or set(parameters) == {"l"}
        else (),
    )
