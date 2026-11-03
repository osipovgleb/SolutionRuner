"""Explicit handler declarations; adding a group needs no runtime branch."""

from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec(
        "right-triangle-642289-sine-opposite",
        "solution_runner.pipelines.triangles.right.group_642289_planner:build_repair_plan",
        inputs=(("parent_condition_asset_id", "parent_asset_id"),),
    ),
    HandlerSpec(
        "right-triangle-acute-angle-difference",
        "solution_runner.pipelines.triangles.right.planner:build_elementary_repair_plan",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
        options=(("content_rule_key", "right-triangle-acute-angle-difference"),),
    ),
    HandlerSpec(
        "right-triangle-acute-angle-ratio",
        "solution_runner.pipelines.triangles.right.planner:build_elementary_repair_plan",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
        options=(("content_rule_key", "right-triangle-acute-angle-ratio"),),
    ),
    HandlerSpec(
        "right-triangle-altitude-bisector-angle",
        "solution_runner.pipelines.triangles.right.construction_ray_parent:prepare",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("content_rule_key", "right-triangle-altitude-bisector-angle"),),
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.right.construction_ray_figures:diagram_specs",
    ),
    HandlerSpec(
        "right-triangle-altitude-bisector-inverse",
        "solution_runner.pipelines.triangles.right.construction_ray_parent:prepare",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("content_rule_key", "right-triangle-altitude-bisector-inverse"),),
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.right.construction_ray_figures:diagram_specs",
    ),
    HandlerSpec(
        "right-triangle-altitude-length",
        "solution_runner.pipelines.triangles.right.degree_parent:prepare",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
        options=(("content_rule_key", "right-triangle-altitude-length"),),
    ),
    HandlerSpec(
        "right-triangle-altitude-line-angle",
        "solution_runner.pipelines.triangles.right.construction_ray_parent:prepare",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("content_rule_key", "right-triangle-altitude-line-angle"),),
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.right.construction_ray_figures:diagram_specs",
    ),
    HandlerSpec(
        "right-triangle-altitude-median-inverse",
        "solution_runner.pipelines.triangles.right.construction_ray_parent:prepare",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("content_rule_key", "right-triangle-altitude-median-inverse"),),
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.right.construction_ray_figures:diagram_specs",
    ),
    HandlerSpec(
        "right-triangle-altitude-universal",
        "solution_runner.pipelines.triangles.right.planner:build_altitude_repair_plan",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
    ),
    HandlerSpec(
        "right-triangle-area-leg-difference",
        "solution_runner.pipelines.triangles.right.planner:build_elementary_repair_plan",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
        options=(("content_rule_key", "right-triangle-area-leg-difference"),),
    ),
    HandlerSpec(
        "right-triangle-bisector-intersection-angle",
        "solution_runner.pipelines.triangles.right.construction_parent:prepare",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
        options=(("content_rule_key", "right-triangle-bisector-intersection-angle"),),
    ),
    HandlerSpec(
        "right-triangle-bisector-median-angle",
        "solution_runner.pipelines.triangles.right.construction_ray_parent:prepare",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("content_rule_key", "right-triangle-bisector-median-angle"),),
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.right.construction_ray_figures:diagram_specs",
    ),
    HandlerSpec(
        "right-triangle-bisector-median-inverse",
        "solution_runner.pipelines.triangles.right.construction_ray_parent:prepare",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("content_rule_key", "right-triangle-bisector-median-inverse"),),
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.right.construction_ray_figures:diagram_specs",
    ),
    HandlerSpec(
        "right-triangle-cosine-hypotenuse",
        "solution_runner.pipelines.triangles.right.planner:build_repair_plan",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
        options=(("required_trig_name", "cos"), ("required_requested", "AB")),
        constraints=(("required_trig_name", "cos"), ("required_requested", "AB")),
    ),
    HandlerSpec(
        "right-triangle-hypotenuse-projection-ah",
        "solution_runner.pipelines.triangles.right.degree_parent:prepare",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
        options=(("content_rule_key", "right-triangle-hypotenuse-projection-ah"),),
    ),
    HandlerSpec(
        "right-triangle-hypotenuse-projection-bh",
        "solution_runner.pipelines.triangles.right.degree_parent:prepare",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
        options=(("content_rule_key", "right-triangle-hypotenuse-projection-bh"),),
    ),
    HandlerSpec(
        "right-triangle-leg-hypotenuse-area",
        "solution_runner.pipelines.triangles.right.planner:build_elementary_repair_plan",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
        options=(("content_rule_key", "right-triangle-leg-hypotenuse-area"),),
    ),
    HandlerSpec(
        "right-triangle-median-angle",
        "solution_runner.pipelines.triangles.right.construction_parent:prepare",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
        options=(("content_rule_key", "right-triangle-median-angle"),),
    ),
    HandlerSpec(
        "right-triangle-sine",
        "solution_runner.pipelines.triangles.right.planner:build_repair_plan",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
    ),
    HandlerSpec(
        "right-triangle-tangent-hypotenuse",
        "solution_runner.pipelines.triangles.right.planner:build_repair_plan",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
        options=(("required_trig_name", "tg"),),
        constraints=(("required_trig_name", "tg"),),
    ),
    HandlerSpec(
        "right-triangle-tangent-opposite-cathetus",
        "solution_runner.pipelines.triangles.right.planner:build_tangent_bc_repair_plan",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
    ),
    HandlerSpec(
        "right-triangle-universal",
        "solution_runner.pipelines.triangles.right.planner:build_universal_repair_plan",
        inputs=(
            ("parent_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
    ),
)
