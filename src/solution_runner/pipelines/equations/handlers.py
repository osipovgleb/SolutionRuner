"""Explicit handler declarations; adding a group needs no runtime branch."""

from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec(
        "quadratic-single-interval-choices",
        "solution_runner.pipelines.equations.quadratic_interval_choices:build_context_repair_plan",
        requires_parent_condition_asset=False,
        strict_frozen_input=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.equations.quadratic_interval_choices:diagram_specs",
        inputs=(("generated_solution_assets", "generated_solution_assets"),),
    ),
    HandlerSpec(
        "quadratic-inequality-graph-choices",
        "solution_runner.pipelines.equations.quadratic_inequality_choices:build_context_repair_plan",
        requires_parent_condition_asset=False,
        strict_frozen_input=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.equations.quadratic_inequality_choices:diagram_specs",
        inputs=(("generated_solution_assets", "generated_solution_assets"),),
    ),
    HandlerSpec(
        "numeric-power-of-power-product",
        "solution_runner.pipelines.equations.numeric_special_forms:build_power_product_plan",
        requires_parent_condition_asset=False,
        inputs=(("parent_solution_html", "parent_solution_html"),),
    ),
    HandlerSpec(
        "numeric-root-product",
        "solution_runner.pipelines.equations.numeric_special_forms:build_root_product_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "inequality-systems-linear-complete",
        "solution_runner.pipelines.equations.inequality_systems_complete:build_context_repair_plan",
        requires_parent_condition_asset=False,
        strict_frozen_input=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.equations.inequality_systems_complete:diagram_specs",
        inputs=(("generated_solution_assets", "generated_solution_assets"),),
    ),
    HandlerSpec(
        "inequality-systems-reviewed-presentation",
        "solution_runner.pipelines.equations.inequality_systems:build_context_repair_plan",
        requires_parent_condition_asset=False,
        presentation_only=True,
    ),
    HandlerSpec(
        "exponential-26650-common-base-affine-exponent",
        "solution_runner.pipelines.equations.group_26650:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "exponential-77379-equal-exponent-different-bases",
        "solution_runner.pipelines.equations.group_77379:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "logarithm-common-normalized",
        "solution_runner.pipelines.equations.group_26646:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "logarithm-77381-shifted-equal-logs",
        "solution_runner.pipelines.equations.group_77381:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "logarithm-77382-affine-base-perfect-power",
        "solution_runner.pipelines.equations.group_77382:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "logarithm-315120-power-argument-common-base",
        "solution_runner.pipelines.equations.group_315120:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "logarithm-315535-exponential-logarithm-affine",
        "solution_runner.pipelines.equations.group_315535:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "trigonometric-table-value-affine-argument",
        "solution_runner.pipelines.equations.group_trigonometric:build_context_repair_plan",
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.equations.group_trigonometric:required_assets",
    ),
    HandlerSpec(
        "numeric-rational-expression-mixed-decimal",
        "solution_runner.pipelines.equations.numeric_rational_expression:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-decimal-sum-difference",
        "solution_runner.pipelines.equations.numeric_rational_expression:build_decimal_sum_difference_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "coordinate-line-true-statement",
        "solution_runner.pipelines.equations.coordinate_line_statement:build_context_repair_plan",
        requires_parent_condition_asset=False,
        inputs=(("condition_asset_bytes", "condition_asset_bytes"),),
        requires_condition_asset_download=True,
    ),
    HandlerSpec(
        "coordinate-line-multiple-values",
        "solution_runner.pipelines.equations.coordinate_line_multiple_values:build_context_repair_plan",
        requires_parent_condition_asset=False,
        inputs=(("condition_asset_bytes", "condition_asset_bytes"),),
        requires_condition_asset_download=True,
    ),
    HandlerSpec(
        "coordinate-line-difference-sign",
        "solution_runner.pipelines.equations.coordinate_line_difference:build_context_repair_plan",
        requires_parent_condition_asset=False,
        inputs=(("condition_asset_bytes", "condition_asset_bytes"),),
        requires_condition_asset_download=True,
    ),
    HandlerSpec(
        "number-comparison-between-options",
        "solution_runner.pipelines.equations.number_comparison:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-decimal-product-ratio",
        "solution_runner.pipelines.equations.numeric_decimal_product_ratio:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-simple-decimal-product",
        "solution_runner.pipelines.equations.numeric_decimal_product_ratio:build_simple_decimal_product_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-square-difference-division",
        "solution_runner.pipelines.equations.numeric_special_forms:build_square_difference_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-fraction-division",
        "solution_runner.pipelines.equations.numeric_special_forms:build_fraction_division_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "numeric-conjugate-product",
        "solution_runner.pipelines.equations.numeric_special_forms:build_conjugate_product_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-expression-cancellation",
        "solution_runner.pipelines.equations.algebraic_expression_cancellation:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-power-cancellation",
        "solution_runner.pipelines.equations.algebraic_power_cancellation:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-polynomial-reciprocal-ratio",
        "solution_runner.pipelines.equations.algebraic_polynomial_ratio:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-complementary-ratio",
        "solution_runner.pipelines.equations.algebraic_complementary_ratio:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-ratio-from-linear-fraction",
        "solution_runner.pipelines.equations.algebraic_ratio_from_linear_fraction:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-shifted-linear-expression",
        "solution_runner.pipelines.equations.algebraic_shifted_linear_expression:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-square-expansion-ratio",
        "solution_runner.pipelines.equations.algebraic_square_expansion_ratio:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-proportional-linear-ratio",
        "solution_runner.pipelines.equations.algebraic_proportional_linear_ratio:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-monomial-ratio",
        "solution_runner.pipelines.equations.algebraic_monomial_ratio:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-linear-function-value",
        "solution_runner.pipelines.equations.algebraic_linear_function_value:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-sum-of-given-expressions",
        "solution_runner.pipelines.equations.algebraic_sum_of_given_expressions:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-linear-function-shift-difference",
        "solution_runner.pipelines.equations.algebraic_linear_function_shift_difference:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-affine-function-combination",
        "solution_runner.pipelines.equations.algebraic_affine_function_combination:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-complementary-affine-sum",
        "solution_runner.pipelines.equations.algebraic_complementary_affine_sum:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-scaled-affine-difference",
        "solution_runner.pipelines.equations.algebraic_scaled_affine_difference:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-conjugate-product-value",
        "solution_runner.pipelines.equations.algebraic_conjugate_product_value:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-conjugate-reciprocal-difference",
        "solution_runner.pipelines.equations.algebraic_conjugate_reciprocal_difference:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "algebraic-conjugate-reciprocal-linear-tail",
        "solution_runner.pipelines.equations.algebraic_conjugate_reciprocal_linear_tail:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-509214-linear-equation",
        "solution_runner.pipelines.equations.group_509214_planner:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-square-root-selector",
        "solution_runner.pipelines.equations.group_square_root_selector:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-101879-equal-numerators",
        "solution_runner.pipelines.equations.group_101879_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-26662-fractional-linear-equation",
        "solution_runner.pipelines.equations.group_26662_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-26663-negative-fractional-linear-equation",
        "solution_runner.pipelines.equations.group_26663_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-26667-quadratic-root-selector",
        "solution_runner.pipelines.equations.group_26667_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-282849-shifted-cube-root",
        "solution_runner.pipelines.equations.group_282849_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-282850-odd-power-root",
        "solution_runner.pipelines.equations.group_282850_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-315119-equal-unit-fractions",
        "solution_runner.pipelines.equations.group_315119_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-77366-rational-square-root-selector",
        "solution_runner.pipelines.equations.group_77366_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-77367-rational-quadratic-selector",
        "solution_runner.pipelines.equations.group_77367_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-77368-equal-squares-first-solution",
        "solution_runner.pipelines.equations.group_77368_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-77369-completed-square",
        "solution_runner.pipelines.equations.group_77369_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-77370-expanded-square-linear",
        "solution_runner.pipelines.equations.group_77370_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-77371-fractional-square-root",
        "solution_runner.pipelines.equations.group_77371_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "elementary-equations-77383-reciprocal-linear",
        "solution_runner.pipelines.equations.group_77383_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("current_asset_content_type", "current_asset_content_type"),
        ),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "irrational-26656-square-root-affine",
        "solution_runner.pipelines.equations.group_26656:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "irrational-511751-reciprocal-square-root",
        "solution_runner.pipelines.equations.group_511751:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "irrational-26660-square-root-rational-affine",
        "solution_runner.pipelines.equations.group_26660:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "irrational-26668-square-root-negative-x",
        "solution_runner.pipelines.equations.group_26668:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "irrational-27466-odd-root-affine",
        "solution_runner.pipelines.equations.group_27466:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
)

HANDLERS += (
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

# Numeric logarithm methods.
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

# Remaining radical methods.
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

# Numeric trigonometric expressions.
HANDLERS += (
    HandlerSpec(
        "numeric-trigonometric-expression",
        "solution_runner.pipelines.equations.trig_numeric:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
)

# Symbolic trigonometric methods.
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


HANDLERS += (
    HandlerSpec(
        "exam-exponential-quadratic-interval",
        "solution_runner.pipelines.equations.exam_exponential:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-exponential-factor-interval",
        "solution_runner.pipelines.equations.exam_factor:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-rational-interval",
        "solution_runner.pipelines.equations.exam_rational:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)
