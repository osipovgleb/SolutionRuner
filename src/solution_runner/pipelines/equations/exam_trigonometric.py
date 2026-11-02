"""Reduce reviewed identities, keep zero factors and select exact periodic roots."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from ..word_problems.math_common import primitive
from . import (
    exam_trigonometric_compile,
    exam_trigonometric_equation,
    exam_trigonometric_inverse,
    exam_trigonometric_selection,
    exam_trigonometric_style,
)
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S, T, U
from .exam_trigonometric_equation import analysis_fields
from .exam_trigonometric_homogeneous import Reduction
from .exam_trigonometric_inverse import (
    ordered,
    select_inverse,
)
from .exam_trigonometric_selection import (
    canonical,
    equivalent_series,
)
from .exam_trigonometric_square_difference import parameter as integer_parameter
from .exam_trigonometric_style import (
    circle_note,
    homogeneous_method,
    parent_style,
    selection_note,
)
from .exam_trigonometric_sum_identities import style as sum_identity_style

method_equation = exam_trigonometric_equation.method_equation
compile_equation = exam_trigonometric_compile.compile_equation
table = exam_trigonometric_compile.table
angles = exam_trigonometric_inverse.angles
method_series = exam_trigonometric_selection.method_series
periodic = exam_trigonometric_selection.periodic
root_series = exam_trigonometric_selection.root_series
division = exam_trigonometric_style.division

if TYPE_CHECKING:
    from .exam_trigonometric_affine import AffineFactor
    from .exam_trigonometric_angle_product import AngleProduct
    from .exam_trigonometric_bounded_log import BoundedLog
    from .exam_trigonometric_exponential_absolute import ExponentialAbsolute
    from .exam_trigonometric_global_radical import GlobalRadical
    from .exam_trigonometric_log_polynomial import LogPolynomial
    from .exam_trigonometric_log_product import LogProduct
    from .exam_trigonometric_original_quotients import OriginalQuotient
    from .exam_trigonometric_power_equality import PowerEquality
    from .exam_trigonometric_power_polynomial import PowerPolynomial
    from .exam_trigonometric_radical_equation import RadicalEquation
    from .exam_trigonometric_radical_product import RadicalProduct
    from .exam_trigonometric_ratio_product import RatioProduct
    from .exam_trigonometric_square_difference import SquareDifference
    from .exam_trigonometric_square_radicals import SquareRadicals
    from .exam_trigonometric_strict_quotient import StrictQuotient
    from .exam_trigonometric_sum_product import SumProduct
    from .exam_trigonometric_symmetric import SumReduction
    from .exam_trigonometric_triple_angle import TripleAngle


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
    square_factor: bool = False
    square_discriminant: bool = False
    square_level: bool = False
    phase_series: tuple = ()


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
    absolute_square: tuple | None = None
    absolute_fraction: tuple | None = None
    radical_ratio: tuple | None = None
    strict_quotient: "StrictQuotient | None" = None
    original_quotient: "OriginalQuotient | None" = None
    radical_product: "RadicalProduct | None" = None
    radical_equation: "RadicalEquation | None" = None
    bounded_log: "BoundedLog | None" = None
    log_product: "LogProduct | None" = None
    log_polynomial: "LogPolynomial | None" = None
    global_radical: "GlobalRadical | None" = None
    square_radicals: "SquareRadicals | None" = None
    exponential_absolute: "ExponentialAbsolute | None" = None
    power_equality: "PowerEquality | None" = None
    power_polynomial: "PowerPolynomial | None" = None
    sum_squares: tuple | None = None
    argument_pair: tuple | None = None
    extremum: tuple | None = None
    sine_pair: tuple | None = None
    cosine_equality: tuple | None = None
    sine_double: tuple | None = None
    positive_factorization: tuple | None = None
    centered_power: tuple | None = None
    division: bool = False
    shifted_notation: bool = False
    homogeneous: Reduction | None = None
    power_angle: sp.Rational | None = None
    factored_source: sp.Expr | None = None
    affine: "AffineFactor | None" = None
    angle_product: "AngleProduct | None" = None
    cleared_denominator: sp.Expr | None = None
    ratio_division: tuple | None = None
    square_difference: "SquareDifference | None" = None
    symmetric: "SumReduction | None" = None
    square_product: tuple | None = None
    unit_factors: tuple | None = None
    sum_product: "SumProduct | None" = None
    triple_angle: "TripleAngle | None" = None
    sine_triple_note: bool = False
    ratio_product: "RatioProduct | None" = None
    selection_note: bool = False
    single_part: bool = False
    sine_inverse: bool = False
    circle_note: bool = False
    auxiliary_notes: bool = False
    four_methods: tuple | None = None
    parameter: str = "k"
    series_aligned: bool = False
    signed_series: tuple = ()
    family_parameters: tuple = ()
    restricted_families: tuple = ()
    radical_notes: tuple = ()
    finite_roots: tuple | None = None


def solve_branches(raw, preferred, allow_inverse=False, *, factored=False, poles=()):
    from .exam_trigonometric_factors import project, separated
    from .exam_trigonometric_grouping import mixed_branches
    from .exam_trigonometric_linear_phase import branch as phased_branch
    from .exam_trigonometric_ratios import linear_branch, ratio_branch

    if raw.has(T, U):
        return ratio_branch(raw, U if raw.has(U) else T)
    if preferred in (T, U):
        return mixed_branches(raw, allow_inverse=allow_inverse)
    if factored:
        from .exam_trigonometric_factors import source_factors

        reduced, expressions = raw, source_factors(raw)
    else:
        reduced, expressions = project(raw, preferred)
    branches = []
    for expression in expressions:
        variables = expression.free_symbols & {S, C}
        if len(variables) != 1:
            mixed = linear_branch(expression) or phased_branch(
                expression, allow_inverse=allow_inverse
            )
            if mixed is not None:
                branches.append(mixed)
                continue
            separate = separated(raw, preferred, allow_inverse)
            return (
                separate
                if separate is not None
                else mixed_branches(raw, allow_inverse=allow_inverse)
            )
        variable = variables.pop()
        p = primitive(expression, (variable,))
        values = roots(p.subs(variable, X))
        accepted = tuple(
            v
            for v in values
            if compare(v, -sp.Integer(1)) >= 0 and compare(v, sp.Integer(1)) <= 0
        )
        from .exam_trigonometric_domain import level_branch

        branches.append(
            level_branch(variable, p, values, accepted, allow_inverse, poles)
        )
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
    if (isinstance(lo, sp.Basic) and lo.has(sp.E)) or (
        isinstance(hi, sp.Basic) and hi.has(sp.E)
    ):
        from .exam_trigonometric_inverse import select_euler

        return select_euler(series, bounds)
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
    from .exam_trigonometric_log_common import numeric_bases

    formula, parent_html = numeric_bases(formula), numeric_bases(parent_html)
    if bounds is None:
        result = analyze(
            formula, r"[0;2\pi)", (sp.S.Zero, 2 * sp.pi, True, False), parent_html
        )
        return replace(
            result, single_part=True, interval="", selected=(), selections=()
        )
    from .exam_trigonometric_auxiliary_notes import split
    from .exam_trigonometric_four_methods import split as split_four
    from .exam_trigonometric_radical_style import split as split_radical

    parent_html, radical_notes = split_radical(parent_html, formula)
    parent_html, four_methods = split_four(parent_html)
    parent_html, auxiliary_notes = split(parent_html)
    from .exam_trigonometric_global_radical import reviewed as global_radical
    from .exam_trigonometric_methods import methods, preference
    from .exam_trigonometric_radical_equation import variable_radicals
    from .exam_trigonometric_radical_style import kind as radical_kind
    from .exam_trigonometric_sine_pair import reviewed as equal_sines
    from .exam_trigonometric_translation import read_method

    if (
        global_radical(parent_html)
        or sum_identity_style(parent_html)
        or equal_sines(parent_html)
        or (radical_kind(parent_html) and variable_radicals(formula))
    ):
        translation, shifted_notation = sp.S.Zero, False
    else:
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
            or not equivalent_series(result.series, second.series)
            or result.selected != second.selected
        ):
            raise UnsupportedCondition(
                "the parent methods must yield identical complete root sets"
            )
        result = replace(result, alternative=second, image_position="after-intro")
    if auxiliary_notes:
        from .exam_trigonometric_auxiliary_notes import finish

        result = finish(result)
    if radical_notes:
        if (
            result.radical_equation is None
            or result.radical_equation.kind != radical_notes[1]
        ):
            raise UnsupportedCondition(
                "every radical note must share the primary equation certificate"
            )
        result = replace(result, radical_notes=radical_notes)
    if four_methods:
        from .exam_trigonometric_four_methods import certify

        result = certify(result)
    from .exam_trigonometric_triple_angle import retain_sine_note

    return retain_sine_note(result, parent_html)


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
        style or parent_style(parent_html, formula=formula)
    )
    if preferred_scale is None:
        _, preferred_scale = preference(parent_html)
    if homogeneous_method(parent_html):
        preferred, preferred_scale = T, sp.S.One
    allow_inverse = method == "inequalities" or any(
        name in parent_html for name in (r"\arccos", r"\arcsin")
    )
    compiled, domain = exam_trigonometric_equation.compile_parent(
        formula, preferred, preferred_scale, translation, parent_html
    )
    if compiled.power_equality is not None or compiled.power_polynomial is not None:
        from .exam_trigonometric_power_style import figure_stage

        grouping = compiled.power_equality.grouping if compiled.power_equality else None
        position = (
            "after-polynomial"
            if (grouping is not None and grouping.figure_after_grouping)
            or (
                compiled.power_polynomial is not None
                and compiled.power_polynomial.style.figure_after_polynomial
            )
            else figure_stage(parent_html)
        )
    from .exam_trigonometric_factors import method_branches

    compiled, reduced, branches, preferred = method_branches(
        compiled, preferred, allow_inverse, domain, parent_html, translation=translation
    )
    if compiled.strict_quotient is not None:
        position = {
            "none": "none",
            "outside": "outside",
            "domain": "after-intro",
            "double_identity": "after-intro",
        }[compiled.strict_quotient.stage]
    if compiled.original_quotient is not None:
        position = compiled.original_quotient.stage
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

    result = finish(
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
            allow_inverse=allow_inverse,
            merged=merged,
            translation=translation,
            division=dividing,
            shifted_notation=shifted_notation,
            selection_note=selection_note(parent_html),
            sine_inverse=r"\arcsin" in parent_html,
            circle_note=circle_note(parent_html),
            parameter=integer_parameter(parent_html),
            **analysis_fields(compiled),
        )
    )

    from .exam_trigonometric_selection import finalize

    return finalize(result, parent_html)


def build_context_repair_plan(
    context, *, parent_solution_html="", generated_solution_assets=()
):
    from .exam_input import repair
    from .exam_trigonometric_circle import image, read
    from .exam_trigonometric_proof import render
    from .expression_repair import with_condition_repair
    from .verified_expression_repair import repair_verified_condition

    context, condition_change = repair_verified_condition(context, validate=read)
    parts, formula, interval, bounds = read(context)
    a = analyze(formula, interval, bounds, parent_solution_html)
    if a.image_position == "none" and context["normalized_content"].get("assets"):
        a = replace(a, image_position="after-steps")
    markup, key, asset_changes = image(
        context, a, generated_solution_assets, parent_html=parent_solution_html
    )
    keys = list(key) if isinstance(key, tuple) else [key] if key else []
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
    return with_condition_repair(
        replace(plan, transformations=tuple(asset_changes) + tuple(changes)),
        condition_change,
    )
