"""Handler declarations for this family of equation runners."""

from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec(
        "exam-logarithm-inequality-square-difference",
        "solution_runner.pipelines.equations.logarithm_inequality_planner:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("method", "square_difference"),),
        diagram_builder="solution_runner.pipelines.equations.logarithm_square_difference_figures:diagram_specs",
        asset_selector="solution_runner.pipelines.equations.logarithm_square_difference_figures:required_assets",
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-logarithm-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.logarithm_rational_substitution_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
    )
    for method in ("rational_log_sum", "rational_log_square", "rational_log_general")
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-logarithm-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.logarithm_rationalization_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
    )
    for method in ("ratio_rationalization", "square_denominator")
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-logarithm-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.logarithm_variable_substitution_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
    )
    for method in ("variable_log_product", "variable_log_reciprocal")
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-logarithm-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.logarithm_variable_comparison_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
    )
    for method in ("base_cancel_quotient", "increasing_cubic_comparison")
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-logarithm-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.logarithm_sign_cases_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
    )
    for method in ("variable_log_product_cases", "variable_log_base_order")
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-logarithm-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.logarithm_single_proof:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        )
        if method == "single_log_product"
        else (("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        diagram_builder="solution_runner.pipelines.equations.logarithm_single_figures:diagram_specs"
        if method == "single_log_product"
        else None,
        asset_selector="solution_runner.pipelines.equations.logarithm_single_figures:required_assets"
        if method == "single_log_product"
        else None,
        requires_parent_condition_asset=False,
    )
    for method in ("single_log_product", "single_log_quotient")
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithm-inequality-reciprocal-sum",
        "solution_runner.pipelines.equations.logarithm_reciprocal_sum_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithm-inequality-double-substitution",
        "solution_runner.pipelines.equations.logarithm_double_substitution_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-logarithm-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.logarithm_polynomial_product_proof:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        )
        if method == "polynomial_log_chart"
        else (("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        diagram_builder="solution_runner.pipelines.equations.logarithm_polynomial_product_figures:diagram_specs"
        if method == "polynomial_log_chart"
        else None,
        asset_selector="solution_runner.pipelines.equations.logarithm_polynomial_product_figures:required_assets"
        if method == "polynomial_log_chart"
        else None,
        requires_parent_condition_asset=False,
    )
    for method in ("polynomial_log_reduction", "polynomial_log_chart")
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithm-inequality-square-factor",
        "solution_runner.pipelines.equations.logarithm_square_factor_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-radical-inequality-three-root",
        "solution_runner.pipelines.equations.radical_inequality_comparison_proof:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        diagram_builder="solution_runner.pipelines.equations.radical_inequality_figures:diagram_specs",
        asset_selector="solution_runner.pipelines.equations.radical_inequality_figures:required_assets",
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-radical-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.radical_inequality_factor_proof:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("method", method),),
        diagram_builder="solution_runner.pipelines.equations.radical_inequality_factor_figures:diagram_specs",
        asset_selector="solution_runner.pipelines.equations.radical_inequality_factor_figures:required_assets",
        requires_parent_condition_asset=False,
    )
    for method in ("squared_quotient", "root_factor")
)


HANDLERS += (
    HandlerSpec(
        "exam-radical-inequality-even-power",
        "solution_runner.pipelines.equations.radical_inequality_even_proof:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        diagram_builder="solution_runner.pipelines.equations.radical_inequality_even_figures:diagram_specs",
        asset_selector="solution_runner.pipelines.equations.radical_inequality_even_figures:required_assets",
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-radical-inequality-difference",
        "solution_runner.pipelines.equations.radical_inequality_difference_proof:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        diagram_builder="solution_runner.pipelines.equations.radical_inequality_difference_figures:diagram_specs",
        asset_selector="solution_runner.pipelines.equations.radical_inequality_difference_figures:required_assets",
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-exponential-radical-comparison",
        "solution_runner.pipelines.equations.exponential_radical_comparison_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-exponential-radical-product",
        "solution_runner.pipelines.equations.exponential_radical_product_proof:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        diagram_builder="solution_runner.pipelines.equations.exponential_radical_product_figures:diagram_specs",
        asset_selector="solution_runner.pipelines.equations.exponential_radical_product_figures:required_assets",
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithm-exponential-quadratic",
        "solution_runner.pipelines.equations.logarithm_exponential_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-logarithmic-power-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.logarithmic_power_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
    )
    for method in ("linear_reciprocity", "square_coordinate")
)


HANDLERS += (
    HandlerSpec(
        "exam-exponential-log-product",
        "solution_runner.pipelines.equations.exponential_log_product_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        asset_selector="solution_runner.pipelines.equations.exponential_log_product_figures:required_assets",
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithm-radical-quotient",
        "solution_runner.pipelines.equations.logarithm_radical_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-absolute-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.absolute_inequality_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
    )
    for method in ("squared_quotient", "affine_substitution")
)


HANDLERS += (
    HandlerSpec(
        "exam-absolute-inequality-quadratic-comparison",
        "solution_runner.pipelines.equations.absolute_quadratic_proof:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        diagram_builder="solution_runner.pipelines.equations.absolute_quadratic_figures:diagram_specs",
        asset_selector="solution_runner.pipelines.equations.absolute_quadratic_figures:required_assets",
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-absolute-power-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.absolute_power_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
    )
    for method in ("reciprocal", "signed_exponent")
)


HANDLERS += (
    HandlerSpec(
        "exam-exponential-log-upper-bound",
        "solution_runner.pipelines.equations.exponential_log_bound_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithm-absolute-fraction",
        "solution_runner.pipelines.equations.logarithm_absolute_fraction_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-absolute-log-power-identity",
        "solution_runner.pipelines.equations.absolute_log_power_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithm-monotonic-range",
        "solution_runner.pipelines.equations.logarithm_monotonic_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithm-factored-power-domain",
        "solution_runner.pipelines.equations.logarithm_factored_power_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-polynomial-logarithm-base-cases",
        "solution_runner.pipelines.equations.polynomial_base_mixed_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        asset_selector="solution_runner.pipelines.equations.polynomial_base_mixed_figures:required_assets",
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithm-reciprocal-square-methods",
        "solution_runner.pipelines.equations.logarithm_reciprocal_square_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-single-logarithm-three-methods",
        "solution_runner.pipelines.equations.single_log_three_methods_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        asset_selector="solution_runner.pipelines.equations.single_log_three_methods_figures:required_assets",
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithm-base-power-cancellation",
        "solution_runner.pipelines.equations.logarithm_base_power_cancellation_proof:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithm-rational-base-cases",
        "solution_runner.pipelines.equations.logarithm_rational_base_proof:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        asset_selector="solution_runner.pipelines.equations.logarithm_rational_base_figures:required_assets",
        diagram_builder="solution_runner.pipelines.equations.logarithm_rational_base_figures:diagram_specs",
        requires_parent_condition_asset=False,
    ),
)
