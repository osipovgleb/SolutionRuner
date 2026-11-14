"""Reuse the exact quotient chart only when every plotted domain, sign and marker agrees."""

import json
from pathlib import Path

from ..probability.common import UnsupportedCondition
from .polynomial_logarithm_cases import PolynomialLogCases, analyze
from .radical_inequality_figures import chart as prepare_chart
from .radical_inequality_figures import selection as select_chart
from .rational_inequality_figures import read_formula
from .rational_inequality_parser import X

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/polynomial-base-mixed.json"
    ).read_text()
)
KEY = "exponential_root_quotient_signs"
ALT = (
    "Знаки дроби на области определения: точка корня исключена, нули числителя включены"
)


def signature(a):
    bound = -a.radicand.subs(X, 0) / a.radicand.coeff(X)
    return {
        "role": "fraction_signs_with_strict_root_domain",
        "points": list(map(str, (bound, *a.points))),
        "closed": [
            bool(a.domain.contains(bound)),
            *(bool(a.solution.contains(p)) for p in a.points),
        ],
        "signs": [None, 1, -1, 1],
        "domain": str(a.domain),
        "solution": str(a.solution),
        "operator": ">=",
    }


def compatible(entry, a):
    return not isinstance(a, PolynomialLogCases) and all(
        entry.get(k) == v for k, v in signature(a).items()
    )


def unreviewed_chart(a):
    raise UnsupportedCondition(
        "the exact reviewed source quotient chart is required; unreviewed diagrams are not substituted"
    )


def selection(context, a):
    if isinstance(a, PolynomialLogCases):
        if context["normalized_content"].get("assets"):
            raise UnsupportedCondition(
                "the reviewed polynomial-log parents have no figures"
            )
        return None, None
    return select_chart(
        context,
        a,
        key=KEY,
        figures=SOURCES["figures"],
        compatible_fn=compatible,
        renderer=unreviewed_chart,
    )


def required_assets(context):
    a = analyze(read_formula(context)[1])
    if isinstance(a, PolynomialLogCases) or context["normalized_content"].get("assets"):
        return ()
    matches = [uid for uid, entry in SOURCES["figures"].items() if compatible(entry, a)]
    return tuple(
        {"source_asset_id": uid, "section_id": "solution:1", "alt_text": ALT}
        for uid in matches[:1]
    )


def chart(context, a):
    if isinstance(a, PolynomialLogCases):
        selection(context, a)
        return "", (), ()
    return prepare_chart(context, a, (), key=KEY, alt=ALT, selector=selection)
