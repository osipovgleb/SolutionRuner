"""Parse isosceles-triangle conditions and build minimal content repairs."""

from __future__ import annotations

from . import planner_build, planner_parse, planner_transforms, planner_types

IsoscelesTrianglePlanError = planner_types.IsoscelesTrianglePlanError


RepairPlan = planner_types.RepairPlan


_section = planner_transforms._section


_plain_html = planner_transforms._plain_html


_formula_text = planner_parse._formula_text


_split_braced = planner_parse._split_braced


_parse_positive_value = planner_parse._parse_positive_value


_latex_number = planner_parse._latex_number


_answer_text = planner_parse._answer_text


_target = planner_transforms._target


_section_transformation = planner_transforms._section_transformation


_asset_transformation = planner_transforms._asset_transformation


_without_asset_markup = planner_transforms._without_asset_markup


_solution_asset_transformation = planner_transforms._solution_asset_transformation


_condition_asset_transformation = planner_transforms._condition_asset_transformation


_condition_image_repairs = planner_transforms._condition_image_repairs


_parse_base_from_sine = planner_parse._parse_base_from_sine


_inline_formulas = planner_parse._inline_formulas


_parse_equal_side_from_base_and_sine = (
    planner_parse._parse_equal_side_from_base_and_sine
)


_solution_html = planner_build._solution_html


_group_27285_solution_html = planner_build._group_27285_solution_html


_request_text = planner_parse._request_text


_inline_assignment = planner_parse._inline_assignment


_build_missing_solution_plan = planner_build._build_missing_solution_plan


_normalized_content = planner_build._normalized_content


_answer_matches = planner_build._answer_matches


build_repair_plan = planner_build.build_repair_plan


from . import planner_side_sine_cosine, planner_side_tangent

build_group_27285_repair_plan = planner_side_sine_cosine.build_group_27285_repair_plan


build_group_27286_repair_plan = planner_side_sine_cosine.build_group_27286_repair_plan


build_group_27287_repair_plan = planner_side_sine_cosine.build_group_27287_repair_plan


build_group_27288_repair_plan = planner_side_tangent.build_group_27288_repair_plan


build_group_27289_repair_plan = planner_side_tangent.build_group_27289_repair_plan


from . import (
    planner_base_cosine_height,
    planner_base_sine_height,
    planner_base_tangent_height,
    planner_height_inverse,
    planner_side_cosine_height,
    planner_side_sine_height,
)

build_group_27320_repair_plan = planner_base_sine_height.build_group_27320_repair_plan


build_group_27321_repair_plan = planner_base_sine_height.build_group_27321_repair_plan


build_group_27322_repair_plan = planner_base_cosine_height.build_group_27322_repair_plan


build_group_27323_repair_plan = planner_base_cosine_height.build_group_27323_repair_plan


build_group_27324_repair_plan = (
    planner_base_tangent_height.build_group_27324_repair_plan
)


build_group_27325_repair_plan = (
    planner_base_tangent_height.build_group_27325_repair_plan
)


build_group_27326_repair_plan = planner_side_sine_height.build_group_27326_repair_plan


build_group_27327_repair_plan = planner_side_sine_height.build_group_27327_repair_plan


build_group_27328_repair_plan = planner_side_cosine_height.build_group_27328_repair_plan


build_group_27329_repair_plan = planner_side_cosine_height.build_group_27329_repair_plan


build_group_27330_repair_plan = planner_height_inverse.build_group_27330_repair_plan


build_group_27331_repair_plan = planner_height_inverse.build_group_27331_repair_plan


from . import (
    planner_angle_conversions,
    planner_angle_relations,
    planner_equilateral,
    planner_external_angles,
    planner_height_angles,
    planner_height_sides,
    planner_included_angle_sides,
    planner_obtuse_altitude,
    planner_obtuse_projection,
    planner_obtuse_ratio,
    planner_side_base_area,
    planner_vertex_area,
)

build_group_27345_repair_plan = planner_obtuse_altitude.build_group_27345_repair_plan


build_group_27346_repair_plan = planner_obtuse_altitude.build_group_27346_repair_plan


build_group_27347_repair_plan = planner_obtuse_altitude.build_group_27347_repair_plan


build_group_27349_repair_plan = planner_obtuse_projection.build_group_27349_repair_plan


build_group_27350_repair_plan = planner_obtuse_projection.build_group_27350_repair_plan


build_group_27351_repair_plan = planner_obtuse_ratio.build_group_27351_repair_plan


build_group_27352_repair_plan = planner_obtuse_ratio.build_group_27352_repair_plan


build_group_27353_repair_plan = planner_obtuse_ratio.build_group_27353_repair_plan


build_group_27589_repair_plan = planner_vertex_area.build_group_27589_repair_plan


build_group_27590_repair_plan = planner_vertex_area.build_group_27590_repair_plan


build_group_27619_repair_plan = planner_side_base_area.build_group_27619_repair_plan


build_group_27620_repair_plan = planner_vertex_area.build_group_27620_repair_plan


build_group_27621_repair_plan = planner_vertex_area.build_group_27621_repair_plan


build_group_27744_repair_plan = planner_angle_conversions.build_group_27744_repair_plan


build_group_27745_repair_plan = planner_angle_conversions.build_group_27745_repair_plan


build_group_27746_repair_plan = planner_angle_conversions.build_group_27746_repair_plan


build_group_27747_repair_plan = planner_angle_conversions.build_group_27747_repair_plan


build_group_27748_repair_plan = planner_angle_conversions.build_group_27748_repair_plan


build_group_27750_repair_plan = planner_angle_relations.build_group_27750_repair_plan


build_group_27754_repair_plan = planner_angle_relations.build_group_27754_repair_plan


build_group_27760_repair_plan = planner_angle_relations.build_group_27760_repair_plan


build_group_27792_repair_plan = planner_equilateral.build_group_27792_repair_plan


build_group_27793_repair_plan = planner_equilateral.build_group_27793_repair_plan


build_group_27794_repair_plan = planner_height_angles.build_group_27794_repair_plan


build_group_27795_repair_plan = planner_height_angles.build_group_27795_repair_plan


build_group_27796_repair_plan = planner_height_angles.build_group_27796_repair_plan


build_group_27797_repair_plan = planner_height_sides.build_group_27797_repair_plan


build_group_27798_repair_plan = planner_height_sides.build_group_27798_repair_plan


build_group_27799_repair_plan = (
    planner_included_angle_sides.build_group_27799_repair_plan
)


build_group_27800_repair_plan = (
    planner_included_angle_sides.build_group_27800_repair_plan
)


build_group_628232_repair_plan = (
    planner_included_angle_sides.build_group_628232_repair_plan
)


build_group_676342_repair_plan = planner_external_angles.build_group_676342_repair_plan


build_group_701874_repair_plan = planner_external_angles.build_group_701874_repair_plan
