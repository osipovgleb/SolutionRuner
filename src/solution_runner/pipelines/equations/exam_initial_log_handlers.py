"""Handler declarations for this family of equation runners."""

from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = tuple(
    HandlerSpec(
        "exam-logarithm-inequality-" + method.replace("_", "-"),
        "solution_runner.pipelines.equations.logarithm_inequality_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", method),),
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.equations.logarithm_factor_figures:required_assets"
        if method == "factor_product"
        else None,
    )
    for method in (
        "factor_sum",
        "factor_product",
        "factor_base_square",
        "factor_three_methods",
    )
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithm-inequality-nested",
        "solution_runner.pipelines.equations.logarithm_inequality_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", "nested"),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "exam-logarithm-inequality-product-cancellation",
        "solution_runner.pipelines.equations.logarithm_inequality_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", "product_cancellation"),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "exam-logarithm-inequality-quadratic-substitution",
        "solution_runner.pipelines.equations.logarithm_inequality_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", "quadratic_substitution"),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "exam-logarithm-inequality-quadratic",
        "solution_runner.pipelines.equations.logarithm_inequality_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", "quadratic"),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "exam-logarithm-inequality-product",
        "solution_runner.pipelines.equations.logarithm_inequality_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "exam-logarithm-inequality-quotient",
        "solution_runner.pipelines.equations.logarithm_inequality_planner:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        options=(("method", "quotient"),),
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.equations.logarithm_quotient_inequality_figures:required_assets",
    ),
)
