"""Explicit handler declarations; adding a group needs no runtime branch."""

from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = (
    *(
        HandlerSpec(
            rule,
            "solution_runner.pipelines.triangles.general.altitude_quad_parent:prepare",
            inputs=(
                ("parent_condition_asset_id", "parent_asset_id"),
                ("parent_solution_html", "parent_solution_html"),
                ("parent_solution_assets", "parent_solution_assets"),
                ("generated_solution_assets", "generated_solution_assets"),
            ),
            options=(("content_rule_key", rule),),
            parent_from_group_listing=True,
            requires_frozen_manifest=True,
            verify_content_readback=True,
            diagram_builder="solution_runner.pipelines.triangles.general.altitude_quad_figures:diagram_specs",
        )
        for rule in (
            "general-triangle-27762-orthocenter-angle",
            "general-triangle-500142-altitudes-obtuse-angle",
        )
    ),
    *(
        HandlerSpec(
            rule,
            "solution_runner.pipelines.triangles.general.incenter_parent:prepare",
            inputs=(
                ("parent_condition_asset_id", "parent_asset_id"),
                ("parent_solution_html", "parent_solution_html"),
                ("parent_solution_assets", "parent_solution_assets"),
                ("generated_solution_assets", "generated_solution_assets"),
            ),
            options=(("content_rule_key", rule),),
            parent_from_group_listing=True,
            requires_frozen_manifest=True,
            verify_content_readback=True,
            diagram_builder="solution_runner.pipelines.triangles.general.incenter_figures:diagram_specs",
        )
        for rule in (
            "general-triangle-27764-incenter-angle",
            "general-triangle-27778-incenter-bisectors-angle",
        )
    ),
    *(
        HandlerSpec(
            rule,
            "solution_runner.pipelines.triangles.general.simple_angle_parent:prepare",
            inputs=(
                ("parent_condition_asset_id", "parent_asset_id"),
                ("parent_solution_html", "parent_solution_html"),
                ("parent_solution_assets", "parent_solution_assets"),
                ("generated_solution_assets", "generated_solution_assets"),
            ),
            options=(("content_rule_key", rule),),
            parent_from_group_listing=True,
            requires_frozen_manifest=True,
            verify_content_readback=True,
            diagram_builder="solution_runner.pipelines.triangles.general.simple_angle_figures:diagram_specs",
        )
        for rule in (
            "general-triangle-27743-exterior-angle",
            "general-triangle-27758-bisector-angle",
            "general-triangle-27759-bisector-exterior-angle",
            "general-triangle-681454-bisector-angle",
        )
    ),
    *(
        HandlerSpec(
            rule,
            "solution_runner.pipelines.triangles.general.midline_parent:prepare",
            inputs=(
                ("parent_condition_asset_id", "parent_asset_id"),
                ("parent_solution_html", "parent_solution_html"),
                ("parent_solution_assets", "parent_solution_assets"),
                ("generated_solution_assets", "generated_solution_assets"),
            ),
            options=(("content_rule_key", rule),),
            parent_from_group_listing=True,
            requires_frozen_manifest=True,
            verify_content_readback=True,
            diagram_builder="solution_runner.pipelines.triangles.general.midline_figures:diagram_specs",
        )
        for rule in (
            "general-triangle-27592-midline-area",
            "general-triangle-317337-midline-small-area-to-total",
            "general-triangle-319058-midline-trapezoid-area",
        )
    ),
    HandlerSpec(
        "general-triangle-27591-area-sas-30",
        "solution_runner.pipelines.triangles.general.planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
        ),
        parent_from_group_listing=True,
        expected_parent_id="79ac61c1-1e29-4010-b3a5-22a628bb98d6",
        strict_frozen_input=True,
        requires_frozen_manifest=True,
        manifest_validator="solution_runner.pipelines.triangles.general.scope_27591:validate_manifest",
    ),
    HandlerSpec(
        "general-triangle-27623-altitude-area-ratio",
        "solution_runner.pipelines.triangles.general.height_area_parent:prepare",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        parent_from_group_listing=True,
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.general.height_area_parent:diagram_specs",
    ),
    HandlerSpec(
        "general-triangle-27752-angle-ratio",
        "solution_runner.pipelines.triangles.general.ratio_planner:build_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
        ),
        parent_from_group_listing=True,
        requires_frozen_manifest=True,
        verify_content_readback=True,
    ),
    HandlerSpec(
        "general-triangle-27757-altitude-angle",
        "solution_runner.pipelines.triangles.general.height_subtraction_parent:prepare",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        parent_from_group_listing=True,
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.general.height_subtraction_figures:diagram_specs",
    ),
    HandlerSpec(
        "general-triangle-27763-altitudes-angle-sum",
        "solution_runner.pipelines.triangles.general.angle_planner:build_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("parent_condition_asset_id", "parent_asset_id"),
        ),
        options=(("rule", "general-triangle-27763-altitudes-angle-sum"),),
        parent_from_group_listing=True,
    ),
    HandlerSpec(
        "general-triangle-27767-altitude-bisector-intersection",
        "solution_runner.pipelines.triangles.general.height_bisector_parent:prepare",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        parent_from_group_listing=True,
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.general.height_bisector_figures:diagram_specs",
    ),
    HandlerSpec(
        "general-triangle-27768-bisector-equal-segments-angle",
        "solution_runner.pipelines.triangles.general.next_group_planner:build_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_assets", "parent_solution_assets"),
        ),
        options=(("rule", "general-triangle-27768-bisector-equal-segments-angle"),),
        parent_from_group_listing=True,
    ),
    HandlerSpec(
        "general-triangle-27769-extension-isosceles-angle",
        "solution_runner.pipelines.triangles.general.next_group_planner:build_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_assets", "parent_solution_assets"),
        ),
        options=(("rule", "general-triangle-27769-extension-isosceles-angle"),),
        parent_from_group_listing=True,
    ),
    HandlerSpec(
        "general-triangle-27776-bisector-congruent-angle",
        "solution_runner.pipelines.triangles.general.next_group_planner:build_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_assets", "parent_solution_assets"),
        ),
        options=(("rule", "general-triangle-27776-bisector-congruent-angle"),),
        parent_from_group_listing=True,
    ),
    HandlerSpec(
        "general-triangle-27777-exterior-bisector-isosceles-angle",
        "solution_runner.pipelines.triangles.general.next_group_planner:build_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_assets", "parent_solution_assets"),
        ),
        options=(("rule", "general-triangle-27777-exterior-bisector-isosceles-angle"),),
        parent_from_group_listing=True,
    ),
    HandlerSpec(
        "general-triangle-27779-orthocenter-altitudes-angle",
        "solution_runner.pipelines.triangles.general.orthocenter_parent:prepare",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        parent_from_group_listing=True,
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.general.orthocenter_figures:diagram_specs",
    ),
    HandlerSpec(
        "general-triangle-510796-extended-altitudes-angle",
        "solution_runner.pipelines.triangles.general.next_group_planner:build_repair_plan",
        inputs=(
            ("parent_solution_html", "parent_solution_html"),
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_assets", "parent_solution_assets"),
        ),
        options=(("rule", "general-triangle-510796-extended-altitudes-angle"),),
        parent_from_group_listing=True,
    ),
    HandlerSpec(
        "general-triangle-561168-obtuse-included-angle-area",
        "solution_runner.pipelines.triangles.general.group_561168_planner:build_repair_plan",
        inputs=(("parent_condition_asset_id", "parent_asset_id"),),
        parent_from_group_listing=True,
    ),
)
