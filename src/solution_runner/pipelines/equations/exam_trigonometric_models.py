"""Immutable analysis records for reviewed trigonometric equations."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import sympy as sp

from .exam_trigonometric_homogeneous import Reduction

if TYPE_CHECKING:
    from .exam_trigonometric_absolute_affine import AbsoluteAffine
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
    from .exam_trigonometric_sine_pair import ArgumentPair
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
    argument_pair: "ArgumentPair | None" = None
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
    absolute_affine: "AbsoluteAffine | None" = None


def analysis_fields(equation):
    return {
        "scale": equation.scale,
        "poles": equation.poles,
        "reciprocal": equation.reciprocal,
        "doubled": equation.doubled,
        "rewritten": equation.rewritten,
        "strict_domain": equation.strict_domain,
        "fraction": equation.fraction,
        "absolute": equation.absolute,
        "absolute_affine": equation.absolute_affine,
        "absolute_square": equation.absolute_square,
        "absolute_fraction": equation.absolute_fraction,
        "radical_ratio": equation.radical_ratio,
        "strict_quotient": equation.strict_quotient,
        "original_quotient": equation.original_quotient,
        "radical_product": equation.radical_product,
        "radical_equation": equation.radical_equation,
        "bounded_log": equation.bounded_log,
        "log_product": equation.log_product,
        "log_polynomial": equation.log_polynomial,
        "global_radical": equation.global_radical,
        "square_radicals": equation.square_radicals,
        "exponential_absolute": equation.exponential_absolute,
        "power_equality": equation.power_equality,
        "power_polynomial": equation.power_polynomial,
        "sum_squares": equation.sum_squares,
        "argument_pair": equation.argument_pair,
        "extremum": equation.extremum,
        "sine_pair": equation.sine_pair,
        "cosine_equality": equation.cosine_equality,
        "sine_double": equation.sine_double,
        "positive_factorization": equation.positive_factorization,
        "homogeneous": equation.homogeneous,
        "power_angle": equation.power_angle,
        "factored_source": equation.factored_source,
        "affine": equation.affine,
        "angle_product": equation.angle_product,
        "cleared_denominator": equation.cleared_denominator,
        "ratio_division": equation.ratio_division,
        "square_difference": equation.square_difference,
        "symmetric": equation.symmetric,
        "square_product": equation.square_product,
        "unit_factors": equation.unit_factors,
        "sum_product": equation.sum_product,
        "triple_angle": equation.triple_angle,
        "ratio_product": equation.ratio_product,
    }
