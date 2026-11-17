"""Handler declarations for this family of equation runners."""

from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = tuple(
    HandlerSpec(
        "exam-rational-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.rational_inequality_planner:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("method", method),),
        requires_parent_condition_asset=False,
        diagram_builder="solution_runner.pipelines.equations.rational_inequality_figures:"
        + diagram,
        asset_selector=(
            "solution_runner.pipelines.equations.rational_inequality_figures:"
            + selector
            if selector
            else None
        ),
    )
    for method, diagram, selector in (
        ("sum_fractions", "diagram_specs", None),
        ("cancelled_fraction", "cancelled_diagram_specs", None),
        ("direct_fraction", "diagram_specs", None),
        ("long_division", "diagram_specs", None),
        ("factor_cancelled", "factor_cancelled_diagram_specs", None),
        ("square_numerator", "diagram_specs", None),
        ("opposite_fractions", "opposite_diagram_specs", "opposite_required_assets"),
        ("vieta_quadratic", "vieta_diagram_specs", None),
        ("cancelled_quadratic_sum", "diagram_specs", None),
        ("quadratic_right", "quadratic_diagram_specs", "quadratic_required_assets"),
        ("cubic_cancel", "cubic_diagram_specs", None),
        ("quadratic_denominators", "denominators_diagram_specs", None),
        ("square_zero", "square_zero_diagram_specs", None),
        ("fraction_division", "fraction_division_diagram_specs", None),
        ("degree_division", "degree_division_diagram_specs", None),
        ("split_cancel", "split_cancel_diagram_specs", None),
        ("quartic_cancel", "quartic_diagram_specs", None),
        ("common_square", "square_diagram_specs", None),
    )
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-rational-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.rational_inequality_planner:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("method", method),),
        requires_parent_condition_asset=False,
        diagram_builder="solution_runner.pipelines.equations.rational_inequality_substitution_figures:"
        + diagram,
        asset_selector=(
            "solution_runner.pipelines.equations.rational_inequality_substitution_figures:"
            + selector
            if selector
            else None
        ),
    )
    for method, diagram, selector in (
        ("affine_radical", "affine_diagram_specs", None),
        ("reciprocal_square", "reciprocal_diagram_specs", "reciprocal_required_assets"),
    )
)


HANDLERS += (
    HandlerSpec(
        "exam-exponential-inequality-common-base",
        "solution_runner.pipelines.equations.exponential_inequality_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-exponential-inequality-" + method,
        "solution_runner.pipelines.equations.exponential_inequality_quadratic_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
    )
    for method in (
        "positive_multiply",
        "reciprocal_substitution",
        "offset_quadratic",
        "reciprocal_roots",
    )
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-exponential-inequality-" + method,
        "solution_runner.pipelines.equations.exponential_inequality_quadratic_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
    )
    for method in (
        "homogeneous",
        "grouped_product",
        "collected_power",
        "symmetric_reciprocal",
        "nested_reciprocal",
    )
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-exponential-inequality-" + method,
        "solution_runner.pipelines.equations.exponential_inequality_quadratic_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
    )
    for method in ("quadratic_range", "quadratic_branches")
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-exponential-inequality-" + method,
        "solution_runner.pipelines.equations.exponential_inequality_quadratic_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
    )
    for method in ("linear_denominator", "grouped_quadratic")
)


HANDLERS += (
    HandlerSpec(
        "exam-exponential-inequality-mixed_substitution",
        "solution_runner.pipelines.equations.exponential_inequality_quadratic_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", "mixed_substitution"),),
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.equations.mixed_substitution_figures:required_assets",
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-exponential-inequality-squared_denominator",
        "solution_runner.pipelines.equations.exponential_inequality_quadratic_planner:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("method", "squared_denominator"),),
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.equations.exponential_squared_denominator_figures:required_assets",
        diagram_builder="solution_runner.pipelines.equations.exponential_squared_denominator_figures:diagram_specs",
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-exponential-inequality-cube_over_square",
        "solution_runner.pipelines.equations.exponential_inequality_quadratic_planner:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("method", "cube_over_square"),),
        requires_parent_condition_asset=False,
        diagram_builder="solution_runner.pipelines.equations.exponential_inequality_cubic_figures:diagram_specs",
        asset_selector="solution_runner.pipelines.equations.exponential_inequality_cubic_figures:required_assets",
    ),
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-rational-exponential-substitution" + ("-chart" if chart else ""),
        "solution_runner.pipelines.equations.rational_exponential_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("requires_chart", chart),),
        requires_parent_condition_asset=False,
        asset_selector=(
            "solution_runner.pipelines.equations.rational_exponential_figures:required_assets"
            if chart
            else None
        ),
    )
    for chart in (False, True)
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-rational-exponential-" + method,
        "solution_runner.pipelines.equations.rational_exponential_planner:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(
            ("method", method),
            ("requires_chart", method == "contained_cancellation"),
        ),
        requires_parent_condition_asset=False,
        diagram_builder=(
            "solution_runner.pipelines.equations.rational_exponential_division_figures:"
            + builder
            if builder
            else None
        ),
        asset_selector=(
            "solution_runner.pipelines.equations.rational_exponential_division_figures:required_assets"
            if method == "contained_cancellation"
            else None
        ),
    )
    for method, builder in (
        ("affine_division", None),
        ("contained_cancellation", "contained_diagram_specs"),
        ("cubic_division", "cubic_diagram_specs"),
    )
)


HANDLERS += tuple(
    HandlerSpec(
        "exam-logarithm-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.logarithm_inequality_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.equations.logarithm_rational_comparison_figures:required_assets"
        if method == "power_quotient"
        else None,
    )
    for method in ("quadratic_quotient", "power_quotient")
)
