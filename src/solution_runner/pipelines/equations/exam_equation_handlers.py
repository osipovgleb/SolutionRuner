"""Handler declarations for this family of equation runners."""

from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = (
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


HANDLERS += (
    HandlerSpec(
        "exam-radical-interval",
        "solution_runner.pipelines.equations.exam_radical:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "exam-nested-radical-interval",
        "solution_runner.pipelines.equations.exam_nested_radical:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithmic-interval",
        "solution_runner.pipelines.equations.exam_logarithmic:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-logarithmic-branches",
        "solution_runner.pipelines.equations.exam_logarithmic_branches:build_context_repair_plan",
        inputs=(("parent_solution_html", "parent_solution_html"),),
        requires_parent_condition_asset=False,
    ),
)


HANDLERS += (
    HandlerSpec(
        "exam-trigonometric-polynomial-circle",
        "solution_runner.pipelines.equations.exam_trigonometric:build_context_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        diagram_builder="solution_runner.pipelines.equations.exam_trigonometric_circle:diagram_specs",
        requires_parent_condition_asset=False,
    ),
)
