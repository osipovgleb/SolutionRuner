"""Handler declarations for this family of equation runners."""

from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec(
        "numeric-positive-power-expression",
        "solution_runner.pipelines.equations.power_expression:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-positive-power-three-methods",
        "solution_runner.pipelines.equations.power_expression:build_context_repair_plan",
        options=(("three_methods", True),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "algebraic-integer-power-expression",
        "solution_runner.pipelines.equations.laurent_expression:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-exponential-function-ratio",
        "solution_runner.pipelines.equations.power_methods:build_function_ratio_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-equal-index-root-ratio",
        "solution_runner.pipelines.equations.power_methods:build_root_ratio_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-shared-radical-factor",
        "solution_runner.pipelines.equations.numeric_special_forms:build_radical_factor_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-shared-radical-two-methods",
        "solution_runner.pipelines.equations.numeric_special_forms:build_radical_factor_plan",
        options=(("two_methods", True),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "numeric-logarithm-expression",
        "solution_runner.pipelines.equations.logarithm_expression:build_context_repair_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-logarithm-complements-two-methods",
        "solution_runner.pipelines.equations.logarithm_expression:build_context_repair_plan",
        options=(("two_methods", "complements"),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-logarithm-fraction-two-methods",
        "solution_runner.pipelines.equations.logarithm_expression:build_context_repair_plan",
        options=(("two_methods", "fraction"),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-logarithm-product-with-proof",
        "solution_runner.pipelines.equations.logarithm_expression:build_context_repair_plan",
        options=(("product_proof", True),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-logarithm-monomial",
        "solution_runner.pipelines.equations.logarithm_monomial:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "algebraic-nonzero-root-power",
        "solution_runner.pipelines.equations.radical_algebraic:build_nonzero_root_power_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-radical-difference-of-squares",
        "solution_runner.pipelines.equations.radical_numeric:build_difference_square_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-radical-common-factor-ratio",
        "solution_runner.pipelines.equations.radical_numeric:build_common_factor_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-radical-binomial-square-ratio",
        "solution_runner.pipelines.equations.radical_numeric:build_binomial_square_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-positive-radical-two-methods",
        "solution_runner.pipelines.equations.radical_laurent:build_context_repair_plan",
        options=(("two_methods", True),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-positive-radical-expression",
        "solution_runner.pipelines.equations.radical_laurent:build_context_repair_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-odd-root-symmetric-ratio",
        "solution_runner.pipelines.equations.radical_symmetry:build_symmetric_ratio_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-odd-root-antisymmetric-sum",
        "solution_runner.pipelines.equations.radical_symmetry:build_antisymmetric_sum_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-square-root-with-upper-bound",
        "solution_runner.pipelines.equations.radical_algebraic:build_upper_bound_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-square-root-interval",
        "solution_runner.pipelines.equations.radical_algebraic:build_interval_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "numeric-trigonometric-expression",
        "solution_runner.pipelines.equations.trig_numeric:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "trigonometric-given-value",
        "solution_runner.pipelines.equations.trig_given:build_context_repair_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "trigonometric-direct-tangent",
        "solution_runner.pipelines.equations.trig_given:build_context_repair_plan",
        options=(("direct_tangent", True),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "trigonometric-given-value-via-cotangent",
        "solution_runner.pipelines.equations.trig_given:build_context_repair_plan",
        options=(("via_cotangent", True),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "trigonometric-tangent-ratio-two-methods",
        "solution_runner.pipelines.equations.trig_given:build_context_repair_plan",
        options=(("two_methods", True),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "trigonometric-square-relation-two-methods",
        "solution_runner.pipelines.equations.trig_relation:build_square_relation_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "trigonometric-tangent-equation",
        "solution_runner.pipelines.equations.trig_relation:build_tangent_equation_plan",
        options=(),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "trigonometric-tangent-equation-divide-first",
        "solution_runner.pipelines.equations.trig_relation:build_tangent_equation_plan",
        options=(("divide_first", True),),
        requires_parent_condition_asset=False,
    ),
)
