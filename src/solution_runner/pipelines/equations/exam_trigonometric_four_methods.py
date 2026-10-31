"""Certify the squared, product-extremum and cosine-extremum notes independently."""

from dataclasses import replace

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_trigonometric_angle_domain import equivalent
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_symmetric import V


def split(html):
    soup = BeautifulSoup(html.replace("\xad", ""), "html.parser")
    text = " ".join(soup.get_text(" ").lower().replace("ё", "е").split())
    formulas = "".join(
        "".join(n["data-inline-latex"].split())
        for n in soup.select("[data-inline-latex]")
    )
    requested = "следующие два решения используют ограниченность" in text
    if not requested:
        return html, False
    if (
        soup.find("img")
        or r"t=\sinx-\cosx" not in formulas
        or "посторонние корни" not in text
        or "приведем еще одно решение" not in text
        or r"\cos(3x-" not in formulas
    ):
        raise UnsupportedCondition(
            "all four reviewed methods without figures are required"
        )
    paragraphs = [
        " ".join(p.get_text(" ").lower().replace("ё", "е").split())
        for p in soup.find_all("p")
    ]
    if (
        sum("приведем другое решение" in t for t in paragraphs) != 1
        or sum("приведем еще одно решение" in t for t in paragraphs) != 1
    ):
        raise UnsupportedCondition("exactly the four reviewed methods must be present")
    headings = [
        p
        for p in soup.find_all("p")
        if p.get_text(strip=True).lower() == "примечание 1."
    ]
    if (
        len(headings) != 1
        or headings[0].find_parent("li") is None
        or headings[0].find_parent("li").get("data-list-marker") != "б)"
    ):
        raise UnsupportedCondition(
            "the four-method notes must follow selection in the second part"
        )
    for node in list(headings[0].next_siblings):
        node.extract()
    headings[0].extract()
    return str(soup), True


def certify(a):
    from .exam_trigonometric_selection import equivalent_series

    if (
        a.symmetric is None
        or a.symmetric.sign != -1
        or a.scale != 1
        or a.poles
        or a.translation
    ):
        raise UnsupportedCondition(
            "the four methods require the signed combined-function cubic"
        )
    combined = S - C
    product = 2 * S * C * combined
    constant = a.raw.subs({S: 0, C: 0})
    weight = sp.cancel((a.raw - constant) / product)
    if weight.free_symbols or weight == 0:
        raise UnsupportedCondition(
            "the original equation must reduce exactly to the signed sine product"
        )
    target = sp.simplify(-constant / weight)
    tau = sp.simplify(target / sp.sqrt(2))
    if tau not in (-1, 1) or roots(a.symmetric.polynomial.subs(V, X)) != (
        -tau * sp.sqrt(2),
    ):
        raise UnsupportedCondition(
            "the primary cubic must have one reviewed extremal real root"
        )
    z = sp.Symbol("z", real=True)
    squared = sp.expand(z * z * (1 - z) - target * target)
    if set(roots(squared.subs(z, X))) != {-sp.S.One}:
        raise UnsupportedCondition(
            "the squared note must have exactly its reviewed real level"
        )
    base = -sp.Rational(1, 4)
    parity = 0 if tau == 1 else 1
    expected = ((base + parity, sp.Integer(2)),)
    if not equivalent_series(a.series, expected):
        raise UnsupportedCondition(
            "every method must recover the complete original root family"
        )
    x = sp.Symbol("x", real=True)
    f = sp.sin(2 * x) * (sp.sin(x) - sp.cos(x))
    if not equivalent(f, sp.sqrt(2) * sp.sin(2 * x) * sp.sin(x - sp.pi / 4)):
        raise UnsupportedCondition("the bounded product requires its exact identity")
    product_families = []
    for sign in (-1, 1):
        q = tau * sign / 2 + sp.Rational(1, 4)
        if sp.simplify(sp.sin(2 * sp.pi * q)) == sign:
            product_families.append((q, sp.Integer(2)))
    if not equivalent_series(tuple(product_families), a.series):
        raise UnsupportedCondition("both bounded-product sign systems must be checked")
    cosine_base = base + (1 if tau == -1 else 0)
    beta = 1 if tau == 1 else 0
    k = sp.Symbol("k", integer=True)
    n = sp.expand((3 * (cosine_base + 2 * k) - sp.Rational(1, 4) - beta) / 2)
    if n.is_integer is not True or not equivalent_series(
        ((cosine_base, sp.Integer(2)),), a.series
    ):
        raise UnsupportedCondition(
            "the cosine note requires an integer-index intersection certificate"
        )
    return replace(a, four_methods=(tau, squared, parity, n))
