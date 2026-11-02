"""Read equal-exponent presentation without reusing the parent's numeric base."""

import re

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_power_parser import PositivePowerParser
from .power_arithmetic import clean


def scaled_angle(parent_html):
    from .exam_trigonometric_compile import C, S
    from .power_arithmetic import ScalarParser

    found = set()
    for node in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]"):
        for term in re.split(
            r"\\(?:iff|Leftrightarrow)", clean(node["data-inline-latex"])
        ):
            match = re.fullmatch(r"\\(sin|cos)2x=([^=]+)", term)
            if match is None:
                continue
            try:
                level = ScalarParser(match[2]).parse()
            except UnsupportedCondition:
                continue
            if not level.free_symbols:
                found.add(S if match[1] == "sin" else C)
    if len(found) > 1:
        raise UnsupportedCondition("one original double-angle power method is required")
    return (next(iter(found)), sp.Integer(2)) if found else None


def figure_stage(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    images = soup.find_all("img")
    if not images:
        return "none"
    if len(images) != 1:
        raise UnsupportedCondition("one original positive-power circle is required")
    image = images[0]
    part = image.find_parent("li")
    before, after = [], []
    seen = False
    for node in (part or soup).descendants:
        if node is image:
            seen = True
        elif getattr(node, "attrs", {}).get("data-inline-latex"):
            (after if seen else before).append(node)
    if part is None:
        if before:
            raise UnsupportedCondition(
                "an outside power circle must retain its leading position"
            )
        return "outside"
    if before:
        if after:
            raise UnsupportedCondition(
                "an intermediate power figure requires its own derivation stage"
            )
        return "after-steps"
    preceding = []
    for node in part.descendants:
        if node is image:
            break
        if isinstance(node, str):
            preceding.append(str(node).strip())
    return "after-intro" if any(preceding) else "before-intro"


def equal_base(parent_html):
    for n in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]"):
        for term in re.split(
            r"\\(?:iff|Leftrightarrow)", clean(n["data-inline-latex"])
        ):
            if term.count("=") != 1:
                continue
            atoms, poles = {}, []
            try:
                nodes = tuple(
                    PositivePowerParser(v.replace("x", r"\alpha"), atoms, poles).parse()
                    for v in term.split("=")
                )
            except UnsupportedCondition:
                continue
            if any(node.kind != "power" for node in nodes):
                continue
            base = nodes[0].children[0].value
            if (
                base.is_Rational is True
                and 0 < base <= 10000
                and base != 1
                and nodes[1].children[0].value == base
            ):
                return base
    return None


def equal_sides(left, right, base, parent_base):
    from .exam_trigonometric_power_equality import prime_logs

    if parent_base is None:
        return None
    left, right = dict(left), dict(right)
    for p in tuple(left):
        if left[p] == right.get(p):
            left.pop(p)
            right.pop(p)
    weights = prime_logs(base)
    p = min(weights)
    a, b = (
        sp.expand(left.get(p, 0) / weights[p]),
        sp.expand(right.get(p, 0) / weights[p]),
    )
    if any(
        sp.expand(values.get(prime, 0) - exponent * weights.get(prime, 0)) != 0
        for values, exponent in ((left, a), (right, b))
        for prime in values.keys() | weights.keys()
    ):
        raise UnsupportedCondition(
            "both complete sides must share the presented base exactly"
        )
    parent_weights = prime_logs(parent_base)
    composite = sp.igcd(0, *(abs(v) for v in parent_weights.values())) > 1
    coefficients = (
        [
            v
            for e in (a, b)
            for v in sp.Poly(e, *sorted(e.free_symbols, key=str)).coeffs()
        ]
        if a.free_symbols and b.free_symbols
        else []
    )
    if composite and coefficients and all(v.is_Integer for v in coefficients):
        divisor = sp.igcd(0, *coefficients)
        base, a, b = base**divisor, a / divisor, b / divisor
    return base, a, b
