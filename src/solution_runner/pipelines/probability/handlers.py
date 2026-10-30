"""Shared probability families; no dispatch by group identifiers."""

from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec(
        "probability-conditioned-dice-table",
        "solution_runner.pipelines.probability.conditioned_dice:build_context_repair_plan",
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.probability.conditioned_dice:asset_requirements",
        diagram_builder="solution_runner.pipelines.probability.conditioned_dice:diagram_specs",
        inputs=(("generated_solution_assets", "generated_solution_assets"),),
    ),
    HandlerSpec(
        "probability-counting-ratios",
        "solution_runner.pipelines.probability.counting:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "probability-fair-dice",
        "solution_runner.pipelines.probability.dice:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "probability-fair-coins",
        "solution_runner.pipelines.probability.coins:build_context_repair_plan",
        requires_parent_condition_asset=False,
        inputs=(("parent_solution_html", "parent_solution_html"),),
    ),
    HandlerSpec(
        "probability-differences-and-frequency",
        "solution_runner.pipelines.probability.rates:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
    HandlerSpec(
        "probability-uniform-integer-outcomes",
        "solution_runner.pipelines.probability.integer_outcomes:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
)

HANDLERS += tuple(
    HandlerSpec(
        "probability-" + key,
        "solution_runner.pipelines.probability."
        + module
        + ":build_context_repair_plan",
        requires_parent_condition_asset=False,
    )
    for key, module in [
        ("bernoulli-events", "bernoulli"),
        ("retry-threshold", "retry_threshold"),
        ("independent-pairs", "independent_pairs"),
        ("event-sets", "event_sets"),
        ("knockout-tournament", "knockout"),
    ]
)

HANDLERS += (
    HandlerSpec(
        "probability-two-source-mixtures",
        "solution_runner.pipelines.probability.mixtures:build_context_repair_plan",
        requires_parent_condition_asset=False,
        inputs=(("parent_solution_html", "parent_solution_html"),),
    ),
    HandlerSpec(
        "probability-custom-dice-bayes",
        "solution_runner.pipelines.probability.custom_dice:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
)

HANDLERS += (
    HandlerSpec(
        "probability-finite-sequences",
        "solution_runner.pipelines.probability.finite_sequences:build_context_repair_plan",
        requires_parent_condition_asset=False,
    ),
)

HANDLERS += (
    HandlerSpec(
        "probability-without-replacement",
        "solution_runner.pipelines.probability.without_replacement:build_context_repair_plan",
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.probability.without_replacement:required_assets",
        diagram_builder="solution_runner.pipelines.probability.without_replacement:diagram_specs",
        inputs=(("generated_solution_assets", "generated_solution_assets"),),
    ),
)

HANDLERS += (
    HandlerSpec(
        "probability-joint-events",
        "solution_runner.pipelines.probability.joint_events:build_context_repair_plan",
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.probability.joint_events:required_assets",
        diagram_builder="solution_runner.pipelines.probability.joint_events:diagram_specs",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
    ),
    HandlerSpec(
        "probability-population-tree",
        "solution_runner.pipelines.probability.retirement:build_context_repair_plan",
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.probability.retirement:required_assets",
        diagram_builder="solution_runner.pipelines.probability.retirement:diagram_specs",
        inputs=(("generated_solution_assets", "generated_solution_assets"),),
    ),
    HandlerSpec(
        "probability-admission-tree",
        "solution_runner.pipelines.probability.admission:build_context_repair_plan",
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.probability.admission:required_assets",
        diagram_builder="solution_runner.pipelines.probability.admission:diagram_specs",
        inputs=(("generated_solution_assets", "generated_solution_assets"),),
    ),
)

HANDLERS += (
    HandlerSpec(
        "probability-dice-stopping",
        "solution_runner.pipelines.probability.dice_stopping:build_context_repair_plan",
        requires_parent_condition_asset=False,
        asset_selector="solution_runner.pipelines.probability.dice_stopping:required_assets",
        diagram_builder="solution_runner.pipelines.probability.dice_stopping:diagram_specs",
        inputs=(("generated_solution_assets", "generated_solution_assets"),),
    ),
)

HANDLERS += (
    HandlerSpec(
        "probability-conditional-diagrams",
        "solution_runner.pipelines.probability.conditional_diagrams:build_context_repair_plan",
        requires_parent_condition_asset=False,
        requires_condition_asset_download=True,
        inputs=(("condition_asset_bytes", "condition_asset_bytes"),),
    ),
)
