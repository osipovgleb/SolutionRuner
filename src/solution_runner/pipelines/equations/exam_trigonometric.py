"""Reduce reviewed identities, keep zero factors and select exact periodic roots."""

import re
from dataclasses import dataclass, replace
from functools import cmp_to_key

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from ..word_problems.math_common import primitive
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S, T, compile_equation, table
from .exam_trigonometric_inverse import (
    angles,
    centred,
    level_series,
    ordered,
    select_inverse,
)


@dataclass(frozen=True)
class Branch:
    variable: sp.Symbol
    polynomial: sp.Expr
    candidates: tuple
    values: tuple
    residues: tuple


@dataclass(frozen=True)
class Analysis:
    original: str
    raw: sp.Expr
    identities: tuple
    reduced: sp.Expr
    branches: tuple
    residues: tuple
    series: tuple
    selected: tuple
    selections: tuple
    interval: str
    bounds: tuple
    preferred: sp.Symbol
    square: bool
    alternating: bool
    image_position: str
    substitution: str | None = None
    selection_method: str = "circle"
    factorization: bool = False
    domain: sp.Expr | None = None
    scale: sp.Rational = sp.S.One
    poles: tuple = ()
    reciprocal: sp.Expr | None = None
    doubled: bool = False
    alternative: "Analysis | None" = None
    allow_inverse: bool = False


def periodic(residues):
    residues = set(residues)
    if not residues:
        return ()
    shifts = sorted(
        {
            sp.Integer(2),
            *((b - a) % 2 for a in residues for b in residues if (b - a) % 2),
        }
    )
    period = next(p for p in shifts if {(q + p) % 2 for q in residues} == residues)
    return tuple((q, period) for q in sorted({q % period for q in residues}))


def solve_branches(raw, preferred, allow_inverse=False):
    if raw.has(T):
        p = primitive(raw, (T,))
        values = roots(p.subs(T, X))
        residues = ordered(q for v in values for q in angles(T, v))
        return raw, (Branch(T, p, values, values, residues),)
    other = S if preferred == C else C
    reduced = sp.expand(sp.rem(raw, S * S + C * C - 1, other))
    if not reduced.has(other):
        expressions = [reduced]
    else:
        alternative = sp.expand(sp.rem(raw, S * S + C * C - 1, preferred))
        if not alternative.has(preferred):
            reduced = alternative
            expressions = [reduced]
        else:
            _, factors = sp.factor_list(raw, S, C)
            expressions = [p for p, _ in factors]
    branches = []
    for expression in expressions:
        variables = expression.free_symbols & {S, C}
        if len(variables) != 1:
            raise UnsupportedCondition(
                "each factor must reduce to one sine or cosine without division"
            )
        variable = variables.pop()
        p = primitive(expression, (variable,))
        values = roots(p.subs(variable, X))
        accepted = tuple(
            v
            for v in values
            if compare(v, -sp.Integer(1)) >= 0 and compare(v, sp.Integer(1)) <= 0
        )
        residues = ordered(
            q
            for v in accepted
            for q in (
                angles(variable, v, True) if allow_inverse else table(variable, v)
            )
        )
        branches.append(Branch(variable, p, values, accepted, residues))
    return reduced, tuple(branches)


def parent_style(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    text = " ".join(soup.get_text(" ", strip=True).replace("\xad", "").lower().split())
    images = soup.find_all("img")
    selection_method = (
        "circle"
        if "окружност" in text
        or (len(images) == 1 and "на указанном промежутке лежат точки" in text)
        or (len(images) == 1 and "среди представленных корней отберём" in text)
        or (len(images) == 1 and "изображается жирной дугой" in text)
        or (len(images) == 1 and "удовлетворяют числа" in text)
        or (len(images) == 1 and "принадлежат корни" in text and "см." in text)
        else "inequalities"
        if "решим неравенства" in text
        else None
    )
    if selection_method is None or any(
        s in text for s in ("другое решение", "еще одно решение", "ещё одно решение")
    ):
        raise UnsupportedCondition(
            "one reviewed circle or inequality selection method is required"
        )
    formulas = [
        "".join(s["data-inline-latex"].split())
        for s in soup.select("[data-inline-latex]")
    ]
    from .exam_trigonometric_methods import preference

    function, _ = preference(parent_html)
    if len(images) != (1 if selection_method == "circle" else 0):
        raise UnsupportedCondition(
            "the parent must identify its trigonometric function and one circle"
        )
    position = "none"
    if images:
        image = images[0]
        part = image.find_parent("li")
        position = (
            "outside"
            if part is None
            else "after-intro"
            if any(str(n).strip() for n in image.previous_siblings)
            else "before-intro"
        )
    substitutions = [
        m
        for f in formulas
        for m in re.findall(r"(?:([ty])=\\(?:sin|cos|tg)x|\\(?:sin|cos|tg)x=([ty]))", f)
    ]
    substitution = next((left or right for left, right in substitutions), None)
    return (
        {"sin": S, "cos": C, "tg": T}[function],
        ("полный квадрат" in text),
        any(re.search(r"\(-\d+\)\^\{?k", f) for f in formulas),
        position,
        substitution,
        selection_method,
    )


def select(series, bounds):
    lo, hi, lc, uc = bounds
    if hi - lo > 20 or max(abs(lo), abs(hi)) > 1000:
        raise UnsupportedCondition(
            "the reviewed interval must have bounded rational multiples of pi"
        )
    if any(not isinstance(q, int) and q.is_Rational is not True for q, _ in series):
        return select_inverse(series, bounds)
    selected = set()
    trace = []
    for offset, period in series:
        start = int(sp.ceiling((lo - offset) / period))
        end = int(sp.floor((hi - offset) / period))
        if not lc and offset + start * period == lo:
            start += 1
        if not uc and offset + end * period == hi:
            end -= 1
        values = tuple(offset + k * period for k in range(start, end + 1))
        selected.update(values)
        trace.append((offset, period, start, end, values))
    return tuple(sorted(selected)), tuple(trace)


def analyze(formula, interval, bounds, parent_html):
    from .exam_trigonometric_methods import methods, preference

    primary, alternative = methods(parent_html)
    result = analyze_method(formula, interval, bounds, primary)
    if alternative is not None:
        function, multiple = preference(alternative)
        style = (
            {"sin": S, "cos": C, "tg": T}[function],
            False,
            False,
            "none",
            None,
            result.selection_method,
        )
        second = analyze_method(
            formula,
            interval,
            bounds,
            alternative,
            style=style,
            preferred_scale=multiple,
        )
        if (
            canonical(result.series) != canonical(second.series)
            or result.selected != second.selected
        ):
            raise UnsupportedCondition(
                "the parent methods must yield identical complete root sets"
            )
        result = replace(result, alternative=second, image_position="after-intro")
    return result


def canonical(series):
    if any(q.is_Rational is not True or p.is_Rational is not True for q, p in series):
        raise UnsupportedCondition(
            "multiple methods require reviewed rational-pi series"
        )
    return select(series, (sp.Integer(0), sp.Integer(2), True, False))[0]


def root_series(branches, residues, domain, allow_inverse):
    if domain is not None:
        series = tuple(s for branch in branches for s in periodic(branch.residues))
    elif (
        all(q.is_Rational for q in residues)
        and len(branches) == 1
        and all(
            power[0] % 2 == 0
            for power in sp.Poly(branches[0].polynomial, branches[0].variable).monoms()
        )
    ):
        series = periodic(residues)
    else:
        series = tuple(
            dict.fromkeys(
                s
                for b in branches
                for v in sorted(
                    b.values, key=cmp_to_key(compare), reverse=(b.variable == C)
                )
                for s in level_series(b.variable, v, allow_inverse)
            )
        )
    return series


def analyze_method(
    formula, interval, bounds, parent_html, *, style=None, preferred_scale=None
):
    from .exam_trigonometric_domain import radical_product, restrict, without_poles
    from .exam_trigonometric_methods import (
        Equation,
        compile_reviewed,
        factorized,
        preference,
    )

    preferred, square, alternating, position, substitution, method = (
        style or parent_style(parent_html)
    )
    if preferred_scale is None:
        _, preferred_scale = preference(parent_html)
    allow_inverse = method == "inequalities" or r"\arccos" in parent_html
    compiled = Equation(sp.Integer(0), (), sp.Integer(1))
    product = radical_product(formula)
    if product is None:
        try:
            raw, identities = compile_equation(formula)
        except UnsupportedCondition:
            compiled = compile_reviewed(formula, preferred, preferred_scale)
            raw, identities = compiled.raw, compiled.identities
        domain = None
    else:
        raw, identities, domain = product
    reduced, branches = solve_branches(raw, preferred, allow_inverse)
    if domain is not None:
        branches = restrict(branches, domain)
    branches = without_poles(branches, compiled.poles)
    if len(branches) == 1:
        preferred = branches[0].variable
    residues = ordered(q for b in branches for q in b.residues)
    series = root_series(branches, residues, domain, allow_inverse)
    series = tuple((q / compiled.scale, p / compiled.scale) for q, p in series)
    if method == "inequalities":
        series = centred(series)
    qbounds = tuple(sp.cancel(b / sp.pi) for b in bounds[:2]) + bounds[2:]
    if any(q.is_Rational is not True for q in qbounds[:2]):
        raise UnsupportedCondition(
            "this circle family requires rational-pi interval endpoints"
        )
    selected, trace = select(series, qbounds)
    return Analysis(
        formula,
        raw,
        identities,
        reduced,
        branches,
        residues,
        series,
        selected,
        trace,
        interval,
        qbounds,
        preferred,
        square,
        alternating,
        position,
        substitution,
        method,
        factorized(parent_html),
        domain,
        compiled.scale,
        compiled.poles,
        compiled.reciprocal,
        compiled.doubled,
        None,
        allow_inverse,
    )


def build_context_repair_plan(
    context, *, parent_solution_html="", generated_solution_assets=()
):
    from .exam_input import repair
    from .exam_trigonometric_circle import image, read
    from .exam_trigonometric_proof import render

    parts, formula, interval, bounds = read(context)
    a = analyze(formula, interval, bounds, parent_solution_html)
    if a.image_position == "none" and context["normalized_content"].get("assets"):
        a = replace(a, image_position="after-steps")
    markup, key, asset_changes = image(context, a, generated_solution_assets)
    keys = [key] if key else []
    plan = repair(parts, *render(a, markup))
    changes = list(plan.transformations)
    if (
        not any(
            t["transformation_target_id"].startswith("section:solution")
            for t in changes
        )
        and (parts[2] or {}).get("asset_keys") != keys
    ):
        from ..word_problems.common import rewrite

        changes.append(rewrite(parts[2], "solution", "Решение", plan.solution_html))
    for t in changes:
        if t["transformation_target_id"].startswith("section:solution"):
            t["value"]["asset_keys"] = keys
    return replace(plan, transformations=tuple(asset_changes) + tuple(changes))
