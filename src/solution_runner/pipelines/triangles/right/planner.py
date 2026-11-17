"""Build verified content repairs from one schema-v3 right-triangle problem."""

from __future__ import annotations

from . import (
    planner_altitude,
    planner_altitude_rows,
    planner_angle_rows,
    planner_area_rows,
    planner_basic,
    planner_common,
    planner_conditions,
    planner_elementary,
    planner_elementary_intro,
    planner_notation,
    planner_transformations,
    planner_universal,
    planner_universal_parse,
    planner_universal_render,
)

_ALTITUDE_CONTENT_VERSION = "10"


RightTrianglePlanError = planner_common.RightTrianglePlanError
RepairPlan = planner_common.RepairPlan


UniversalRightTriangleValues = planner_universal_parse.UniversalRightTriangleValues
UniversalTrigRequestValues = planner_universal_parse.UniversalTrigRequestValues


_section = planner_common._section


_plain_html = planner_conditions._plain_html
_latin_triangle_labels = planner_conditions._latin_triangle_labels
_opposite_side = planner_universal_parse._opposite_side
_normalized_trig_formula = planner_universal_parse._normalized_trig_formula
_right_angle_labels = planner_universal_parse._right_angle_labels
_universal_values = planner_universal_parse._universal_values
_universal_trig_request_values = planner_universal_parse._universal_trig_request_values
_latex_values = planner_universal_parse._latex_values
_trig_square = planner_notation._trig_square
_fraction_latex = planner_notation._fraction_latex
_positive_root_latex = planner_notation._positive_root_latex
_canonical_trig_latex = planner_notation._canonical_trig_latex
_decimal_reduction_latex = planner_notation._decimal_reduction_latex


_is_pipeline_verbose_solution = planner_basic._is_pipeline_verbose_solution


_is_pipeline_unsimplified_root_solution = (
    planner_basic._is_pipeline_unsimplified_root_solution
)


_numeric_latex = planner_notation._numeric_latex
_numeric_square_latex = planner_notation._numeric_square_latex
_answer_text = planner_notation._answer_text
_number_latex = planner_notation._number_latex
_positive_root_number_latex = planner_notation._positive_root_number_latex
_asset_transformation = planner_transformations._asset_transformation
_solution_transformation = planner_transformations._solution_transformation


_tangent_solution_transformation = (
    planner_transformations._tangent_solution_transformation
)


_tangent_bc_solution_transformation = (
    planner_transformations._tangent_bc_solution_transformation
)


_answer_transformation = planner_transformations._answer_transformation


_elementary_solution_transformation = (
    planner_transformations._elementary_solution_transformation
)


_integer_match = planner_conditions._integer_match
_leg_hypotenuse_area_rows = planner_area_rows._leg_hypotenuse_area_rows
_area_leg_difference_rows = planner_area_rows._area_leg_difference_rows
_acute_angle_difference_rows = planner_area_rows._acute_angle_difference_rows
_acute_angle_ratio = planner_conditions._acute_angle_ratio
_acute_angle_ratio_rows = planner_area_rows._acute_angle_ratio_rows
_condition_degree_values = planner_conditions._condition_degree_values
_math_aware_html = planner_conditions._math_aware_html
_acute_condition_angles = planner_conditions._acute_condition_angles
_require_condition_terms = planner_conditions._require_condition_terms
_single_acute_angle = planner_conditions._single_acute_angle
_single_line_angle = planner_conditions._single_line_angle
_median_angle_rows = planner_angle_rows._median_angle_rows
_bisector_intersection_angle_rows = planner_angle_rows._bisector_intersection_angle_rows
_altitude_bisector_angle_rows = planner_angle_rows._altitude_bisector_angle_rows
_inverse_45_degree_rows = planner_angle_rows._inverse_45_degree_rows
_altitude_bisector_inverse_rows = planner_angle_rows._altitude_bisector_inverse_rows
_altitude_line_angle_rows = planner_angle_rows._altitude_line_angle_rows
_altitude_median_inverse_rows = planner_angle_rows._altitude_median_inverse_rows
_bisector_median_angle_rows = planner_angle_rows._bisector_median_angle_rows
_bisector_median_inverse_rows = planner_angle_rows._bisector_median_inverse_rows
_angle_a_and_hypotenuse = planner_conditions._angle_a_and_hypotenuse
_altitude_length_rows = planner_altitude_rows._altitude_length_rows
_projection_rows = planner_altitude_rows._projection_rows
_hypotenuse_projection_ah_rows = planner_altitude_rows._hypotenuse_projection_ah_rows
_hypotenuse_projection_bh_rows = planner_altitude_rows._hypotenuse_projection_bh_rows


_ELEMENTARY_RULES = planner_elementary._ELEMENTARY_RULES


_elementary_intro = planner_elementary_intro._elementary_intro


build_elementary_repair_plan = planner_elementary.build_elementary_repair_plan


_parent_triangle_plan = planner_common._parent_triangle_plan


build_repair_plan = planner_basic.build_repair_plan


build_universal_repair_plan = planner_universal.build_universal_repair_plan


build_altitude_repair_plan = planner_altitude.build_altitude_repair_plan


_altitude_step_intro = planner_altitude._altitude_step_intro


_build_universal_trig_request_plan = (
    planner_universal._build_universal_trig_request_plan
)


_answer_matches = planner_common._answer_matches


_universal_solution_transformation = (
    planner_universal_render._universal_solution_transformation
)


_universal_solution_rows_transformation = (
    planner_universal_render._universal_solution_rows_transformation
)


_universal_trig_request_solution_transformation = (
    planner_universal_render._universal_trig_request_solution_transformation
)


build_tangent_bc_repair_plan = planner_basic.build_tangent_bc_repair_plan
