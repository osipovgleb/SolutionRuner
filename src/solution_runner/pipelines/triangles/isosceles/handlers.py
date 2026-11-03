"""Explicit handler declarations; adding a group needs no runtime branch."""

from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec(
        "isosceles-triangle-27284-base-from-sine",
        "solution_runner.pipelines.triangles.isosceles.basic_parent:prepare",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("content_rule_key", "isosceles-triangle-27284-base-from-sine"),),
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.isosceles.basic_figures:diagram_specs",
    ),
    HandlerSpec(
        "isosceles-triangle-27285-side-from-base-sine",
        "solution_runner.pipelines.triangles.isosceles.basic_parent:prepare",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("content_rule_key", "isosceles-triangle-27285-side-from-base-sine"),),
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.isosceles.basic_figures:diagram_specs",
    ),
    HandlerSpec(
        "isosceles-triangle-27286-base-from-cosine",
        "solution_runner.pipelines.triangles.isosceles.basic_parent:prepare",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("content_rule_key", "isosceles-triangle-27286-base-from-cosine"),),
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.isosceles.basic_figures:diagram_specs",
    ),
    HandlerSpec(
        "isosceles-triangle-27287-side-from-base-cosine",
        "solution_runner.pipelines.triangles.isosceles.basic_parent:prepare",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(
            ("content_rule_key", "isosceles-triangle-27287-side-from-base-cosine"),
        ),
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.isosceles.basic_figures:diagram_specs",
    ),
    HandlerSpec(
        "isosceles-triangle-27288-base-from-tangent",
        "solution_runner.pipelines.triangles.isosceles.basic_parent:prepare",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("content_rule_key", "isosceles-triangle-27288-base-from-tangent"),),
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.isosceles.basic_figures:diagram_specs",
    ),
    HandlerSpec(
        "isosceles-triangle-27289-side-from-base-tangent",
        "solution_runner.pipelines.triangles.isosceles.basic_parent:prepare",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(
            ("content_rule_key", "isosceles-triangle-27289-side-from-base-tangent"),
        ),
        requires_frozen_manifest=True,
        verify_content_readback=True,
        diagram_builder="solution_runner.pipelines.triangles.isosceles.basic_figures:diagram_specs",
    ),
    *(
        HandlerSpec(
            rule,
            "solution_runner.pipelines.triangles.isosceles.side_altitude_parent:prepare",
            inputs=(
                ("parent_condition_asset_id", "parent_asset_id"),
                ("parent_solution_html", "parent_solution_html"),
                ("parent_solution_assets", "parent_solution_assets"),
                ("generated_solution_assets", "generated_solution_assets"),
            ),
            options=(("content_rule_key", rule),),
            requires_frozen_manifest=True,
            verify_content_readback=True,
            diagram_builder="solution_runner.pipelines.triangles.isosceles.side_altitude_figures:diagram_specs",
        )
        for rule in (
            "isosceles-triangle-27320-altitude-from-base-sine",
            "isosceles-triangle-27321-projection-from-base-sine",
            "isosceles-triangle-27322-altitude-from-base-cosine",
            "isosceles-triangle-27323-projection-from-base-cosine",
            "isosceles-triangle-27324-altitude-from-base-tangent",
            "isosceles-triangle-27325-projection-from-base-tangent",
            "isosceles-triangle-27326-altitude-from-side-sine",
            "isosceles-triangle-27327-projection-from-side-sine",
            "isosceles-triangle-27328-altitude-from-side-cosine",
            "isosceles-triangle-27329-projection-from-side-cosine",
            "isosceles-triangle-27330-sine-from-altitude-and-base",
            "isosceles-triangle-27331-cosine-from-altitude-and-base",
        )
    ),
    *(
        HandlerSpec(
            rule,
            "solution_runner.pipelines.triangles.isosceles.obtuse_parent:prepare",
            inputs=(
                ("parent_condition_asset_id", "parent_asset_id"),
                ("parent_solution_html", "parent_solution_html"),
                ("parent_solution_assets", "parent_solution_assets"),
                ("generated_solution_assets", "generated_solution_assets"),
            ),
            options=(("content_rule_key", rule),),
            requires_frozen_manifest=True,
            verify_content_readback=True,
            diagram_builder="solution_runner.pipelines.triangles.isosceles.obtuse_figures:diagram_specs",
        )
        for rule in (
            "isosceles-triangle-27345-obtuse-sine-from-side-and-altitude",
            "isosceles-triangle-27346-obtuse-cosine-from-side-and-altitude",
            "isosceles-triangle-27347-obtuse-tangent-from-side-and-altitude",
            "isosceles-triangle-27349-obtuse-cosine-from-side-and-projection",
            "isosceles-triangle-27350-obtuse-tangent-from-side-and-projection",
            "isosceles-triangle-27351-obtuse-sine-from-altitude-and-projection",
            "isosceles-triangle-27352-obtuse-cosine-from-altitude-and-projection",
            "isosceles-triangle-27353-obtuse-tangent-from-altitude-and-projection",
        )
    ),
    *(
        HandlerSpec(
            rule,
            "solution_runner.pipelines.triangles.isosceles.area_parent:prepare",
            inputs=(
                ("parent_condition_asset_id", "parent_asset_id"),
                ("parent_solution_html", "parent_solution_html"),
                ("parent_solution_assets", "parent_solution_assets"),
                ("generated_solution_assets", "generated_solution_assets"),
            ),
            options=(("content_rule_key", rule),),
            requires_frozen_manifest=True,
            verify_content_readback=True,
            diagram_builder="solution_runner.pipelines.triangles.isosceles.area_figures:diagram_specs",
        )
        for rule in (
            "isosceles-triangle-27589-area-from-side-and-30-degree-vertex-angle",
            "isosceles-triangle-27590-area-from-side-and-150-degree-vertex-angle",
            "isosceles-triangle-27619-area-from-side-and-base",
            "isosceles-triangle-27620-side-from-area-and-30-degree-vertex-angle",
            "isosceles-triangle-27621-side-from-area-and-150-degree-vertex-angle",
        )
    ),
    *(
        HandlerSpec(
            rule,
            "solution_runner.pipelines.triangles.isosceles.angle_parent:prepare",
            inputs=(
                ("parent_condition_asset_id", "parent_asset_id"),
                ("parent_solution_html", "parent_solution_html"),
                ("parent_solution_assets", "parent_solution_assets"),
                ("generated_solution_assets", "generated_solution_assets"),
            ),
            options=(("content_rule_key", rule),),
            requires_frozen_manifest=True,
            verify_content_readback=True,
            diagram_builder="solution_runner.pipelines.triangles.isosceles.angle_figures:diagram_specs",
        )
        for rule in (
            "isosceles-triangle-27744-vertex-angle-from-base-angle",
            "isosceles-triangle-27745-base-angle-from-vertex-angle",
            "isosceles-triangle-27746-exterior-angle-from-vertex-angle",
            "isosceles-triangle-27747-vertex-angle-from-exterior-base-angle",
            "isosceles-triangle-27748-base-angle-from-exterior-vertex-angle",
            "isosceles-triangle-27750-smaller-angle-from-larger-angle",
            "isosceles-triangle-27754-smaller-angle-from-angle-difference",
            "isosceles-triangle-27760-vertex-angle-from-altitude-angle",
        )
    ),
    *(
        HandlerSpec(
            rule,
            "solution_runner.pipelines.triangles.isosceles.base_height_parent:prepare",
            inputs=(
                ("parent_condition_asset_id", "parent_asset_id"),
                ("parent_solution_html", "parent_solution_html"),
                ("parent_solution_assets", "parent_solution_assets"),
                ("generated_solution_assets", "generated_solution_assets"),
            ),
            options=(("content_rule_key", rule),),
            requires_frozen_manifest=True,
            verify_content_readback=True,
            diagram_builder="solution_runner.pipelines.triangles.isosceles.base_height_figures:diagram_specs",
        )
        for rule in (
            "isosceles-triangle-27792-equilateral-height-from-side",
            "isosceles-triangle-27793-equilateral-side-from-height",
            "isosceles-triangle-27794-vertex-angle-from-base-altitude",
        )
    ),
    *(
        HandlerSpec(
            rule,
            "solution_runner.pipelines.triangles.isosceles.vertex_altitude_parent:prepare",
            inputs=(
                ("parent_condition_asset_id", "parent_asset_id"),
                ("parent_solution_html", "parent_solution_html"),
                ("parent_solution_assets", "parent_solution_assets"),
                ("generated_solution_assets", "generated_solution_assets"),
            ),
            options=(("content_rule_key", rule),),
            requires_frozen_manifest=True,
            verify_content_readback=True,
            diagram_builder="solution_runner.pipelines.triangles.isosceles.vertex_altitude_figures:diagram_specs",
        )
        for rule in (
            "isosceles-triangle-27795-altitude-from-side-vertex-angle",
            "isosceles-triangle-27796-angle-from-side-altitude",
            "isosceles-triangle-27797-side-from-altitude-vertex-angle",
            "isosceles-triangle-27798-obtuse-altitude-from-side-angle",
        )
    ),
    *(
        HandlerSpec(
            rule,
            "solution_runner.pipelines.triangles.isosceles.cosine_parent:prepare",
            inputs=(
                ("parent_condition_asset_id", "parent_asset_id"),
                ("parent_solution_html", "parent_solution_html"),
                ("parent_solution_assets", "parent_solution_assets"),
                ("generated_solution_assets", "generated_solution_assets"),
            ),
            options=(("content_rule_key", rule),),
            requires_frozen_manifest=True,
            verify_content_readback=True,
            diagram_builder="solution_runner.pipelines.triangles.isosceles.cosine_figures:diagram_specs",
        )
        for rule in (
            "isosceles-triangle-27799-side-from-base-vertex-angle",
            "isosceles-triangle-27800-base-from-side-vertex-angle",
        )
    ),
    HandlerSpec(
        "isosceles-triangle-628232-base-from-side-tangent",
        "solution_runner.pipelines.triangles.isosceles.planner:build_group_628232_repair_plan",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_assets", "parent_solution_assets"),
        ),
    ),
    HandlerSpec(
        "isosceles-triangle-676342-base-angle-from-exterior-angle",
        "solution_runner.pipelines.triangles.isosceles.planner:build_group_676342_repair_plan",
        inputs=(("parent_condition_asset_id", "parent_asset_id"),),
    ),
    HandlerSpec(
        "isosceles-triangle-701874-base-angle-from-apex-exterior-angle",
        "solution_runner.pipelines.triangles.isosceles.planner:build_group_701874_repair_plan",
        inputs=(("parent_condition_asset_id", "parent_asset_id"),),
    ),
)
