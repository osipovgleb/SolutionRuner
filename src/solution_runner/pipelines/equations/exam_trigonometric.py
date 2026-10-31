"""Reduce reviewed identities, keep zero factors and select exact periodic roots."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from ..word_problems.math_common import primitive
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S, T, U, compile_equation, table
from .exam_trigonometric_homogeneous import Reduction
from .exam_trigonometric_inverse import (
    angles,
    ordered,
    select_inverse,
)
from .exam_trigonometric_selection import canonical, periodic, root_series
from .exam_trigonometric_square_difference import reviewed as difference_method
from .exam_trigonometric_style import (
    division,
    grouping_method,
    homogeneous_method,
    parent_style,
)

if TYPE_CHECKING:
    from .exam_trigonometric_affine import AffineFactor
    from .exam_trigonometric_angle_product import AngleProduct
    from .exam_trigonometric_square_difference import SquareDifference
    from .exam_trigonometric_symmetric import SumReduction


@dataclass(frozen=True)
class Branch:
    variable: sp.Symbol
    polynomial: sp.Expr
    candidates: tuple
    values: tuple
    residues: tuple
    original: sp.Expr | None = None
    excluded: tuple = ()
    impossible: bool = False
    grouping: bool = False
    angle_shift: sp.Rational = sp.S.Zero
    angle_scale: sp.Rational = sp.S.One
    quadratic_common: bool = False


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
    scale: sp.Expr = sp.S.One
    poles: tuple = ()
    reciprocal: sp.Expr | None = None
    doubled: bool = False
    alternative: "Analysis | None" = None
    allow_inverse: bool = False
    rewritten: sp.Expr | None = None
    merged: bool = False
    translation: sp.Rational = sp.S.Zero
    strict_domain: bool = False
    fraction: sp.Expr | None = None
    absolute: tuple | None = None
    division: bool = False
    shifted_notation: bool = False
    homogeneous: Reduction | None = None
    power_angle: sp.Rational | None = None
    factored_source: sp.Expr | None = None
    affine: "AffineFactor | None" = None
    angle_product: "AngleProduct | None" = None
    cleared_denominator: sp.Expr | None = None
    square_difference: "SquareDifference | None" = None
    symmetric: "SumReduction | None" = None


def solve_branches(raw, preferred, allow_inverse=False, *, factored=False):
    from .exam_trigonometric_factors import project, separated
    from .exam_trigonometric_grouping import mixed_branches
    from .exam_trigonometric_linear_phase import branch as phased_branch
    from .exam_trigonometric_ratios import linear_branch, ratio_branch

    if raw.has(T, U):
        return ratio_branch(raw, U if raw.has(U) else T)
    if preferred in (T, U):
        return mixed_branches(raw)
    if factored:
        from .exam_trigonometric_factors import source_factors

        reduced, expressions = raw, source_factors(raw)
    else:
        reduced, expressions = project(raw, preferred)
    branches = []
    for expression in expressions:
        variables = expression.free_symbols & {S, C}
        if len(variables) != 1:
            mixed = linear_branch(expression) or phased_branch(expression)
            if mixed is not None:
                branches.append(mixed)
                continue
            separate = separated(raw, preferred, allow_inverse)
            return separate if separate is not None else mixed_branches(raw)
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
    if any(b.original is not None for b in branches):
        reduced = raw
    if factored:
        zero = S if sp.rem(raw, S * S, S) == 0 else C
        branches.sort(key=lambda b: b.variable != zero)
    return reduced, tuple(sorted(branches, key=lambda b: b.original is not None))


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
    from .exam_trigonometric_translation import read_method

    parent_html, translation, shifted_notation = read_method(parent_html)
    primary, alternative = methods(parent_html)
    result = analyze_method(
        formula,
        interval,
        bounds,
        primary,
        translation=translation,
        shifted_notation=shifted_notation,
    )
    if alternative is not None:
        function, multiple = preference(alternative)
        style = (
            {"sin": S, "cos": C, "tg": T, "ctg": U}[function],
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


def method_equation(
    formula, preferred, scale, translation, *, grouping=False, difference=False
):
    from .exam_trigonometric_absolute import compile_absolute
    from .exam_trigonometric_domain import radical_product
    from .exam_trigonometric_methods import Equation, compile_reviewed
    from .exam_trigonometric_radical_quotient import compile_quotient

    absolute = compile_absolute(formula)
    if absolute is not None:
        return absolute, None

    quotient = compile_quotient(formula)
    if quotient is not None:
        return quotient, quotient.domain

    product = radical_product(formula)
    if product is not None:
        if translation:
            raise UnsupportedCondition(
                "translated radical products need a reviewed domain"
            )
        raw, identities, domain = product
        return Equation(raw, identities, sp.S.One), domain
    if scale != 1 or translation or difference:
        return compile_reviewed(
            formula, preferred, scale, translation, difference=difference
        ), None
    try:
        raw, identities = compile_equation(formula, allow_cubic=grouping)
    except UnsupportedCondition:
        return compile_reviewed(
            formula, preferred, scale, translation, difference=difference
        ), None
    return Equation(raw, identities, sp.S.One), None


def analyze_method(
    formula,
    interval,
    bounds,
    parent_html,
    *,
    style=None,
    preferred_scale=None,
    translation=sp.S.Zero,
    shifted_notation=False,
):
    from .exam_trigonometric_methods import (
        factorized,
        preference,
    )

    preferred, square, alternating, position, substitution, method = (
        style or parent_style(parent_html)
    )
    if preferred_scale is None:
        _, preferred_scale = preference(parent_html)
    if homogeneous_method(parent_html):
        preferred, preferred_scale = T, sp.S.One
    allow_inverse = method == "inequalities" or r"\arccos" in parent_html
    compiled, domain = method_equation(
        formula,
        preferred,
        preferred_scale,
        translation,
        grouping=grouping_method(parent_html),
        difference=difference_method(parent_html),
    )
    from .exam_trigonometric_factors import method_branches

    compiled, reduced, branches, preferred = method_branches(
        compiled, preferred, allow_inverse, domain, parent_html, translation=translation
    )
    raw, identities = compiled.raw, compiled.identities
    if len(branches) == 1:
        preferred = branches[0].variable
    residues = ordered(q for b in branches for q in b.residues)
    series, merged, dividing = method_series(
        branches,
        residues,
        compiled,
        domain,
        parent_html,
        (preferred, method),
    )
    qbounds = tuple(sp.cancel(b / sp.pi) for b in bounds[:2]) + bounds[2:]
    from .exam_trigonometric_selection import finish

    return finish(
        Analysis(
            formula,
            raw,
            identities,
            reduced,
            branches,
            residues,
            series,
            (),
            (),
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
            compiled.rewritten,
            merged,
            translation,
            compiled.strict_domain,
            compiled.fraction,
            compiled.absolute,
            dividing,
            shifted_notation,
            compiled.homogeneous,
            compiled.power_angle,
            compiled.factored_source,
            compiled.affine,
            compiled.angle_product,
            compiled.cleared_denominator,
            compiled.square_difference,
            compiled.symmetric,
        )
    )


def method_series(
    branches,
    residues,
    compiled,
    domain,
    parent_html,
    style,
):
    from .exam_trigonometric_methods import merges_series

    preferred, method = style
    allow_inverse = method == "inequalities" or r"\arccos" in parent_html
    merged = (
        (
            method == "inequalities"
            and compiled.scale != 1
            and merges_series(parent_html)
        )
        or compiled.square_difference is not None
        or compiled.symmetric is not None
    )
    dividing = (
        division(parent_html)
        and compiled.homogeneous is None
        and not any(b.original is not None for b in branches)
    )
    if compiled.absolute is not None:
        from .exam_trigonometric_absolute import series as absolute_series

        series = absolute_series(branches[0].values)
    elif dividing:
        from .exam_trigonometric_division import series as division_series

        series = division_series(branches)
    elif merged:
        series = periodic(residues)
    else:
        filtered = domain is not None or (
            compiled.poles and compiled.reciprocal is None and preferred not in (T, U)
        )
        series = root_series(
            branches, residues, filtered if filtered else None, allow_inverse
        )
    return series, merged, dividing


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
