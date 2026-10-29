"""Explicit planner declarations for informatics."""

from solution_runner.pipelines.core.handlers import HandlerSpec


HANDLERS = (
    HandlerSpec(
        "informatics-pass-expiry-bytes",
        "solution_runner.pipelines.informatics.pass_expiry:build_context_repair_plan",
        requires_parent_condition_asset=False,
        parent_from_group_listing=True,
        verify_content_readback=True,
    ),
    HandlerSpec(
        "informatics-pass-two-departments-extra-bytes",
        "solution_runner.pipelines.informatics.pass_two_departments:build_context_repair_plan",
        requires_parent_condition_asset=False,
        parent_from_group_listing=True,
        verify_content_readback=True,
    ),
    HandlerSpec(
        "informatics-pass-department-extra-bytes",
        "solution_runner.pipelines.informatics.pass_department:build_context_repair_plan",
        requires_parent_condition_asset=False,
        parent_from_group_listing=True,
        verify_content_readback=True,
    ),
    HandlerSpec(
        "informatics-password-total-bytes",
        "solution_runner.pipelines.informatics.password_total_bytes:build_context_repair_plan",
        requires_parent_condition_asset=False,
        parent_from_group_listing=True,
        verify_content_readback=True,
    ),
    HandlerSpec(
        "informatics-password-extra-bytes",
        "solution_runner.pipelines.informatics.password_extra_bytes:build_context_repair_plan",
        requires_parent_condition_asset=False,
        parent_from_group_listing=True,
        verify_content_readback=True,
    ),
)
