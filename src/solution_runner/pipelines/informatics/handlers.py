"""Explicit planner declarations for informatics."""

from solution_runner.pipelines.core.handlers import HandlerSpec


HANDLERS = (
    HandlerSpec(
        "informatics-password-extra-bytes",
        "solution_runner.pipelines.informatics.password_extra_bytes:build_context_repair_plan",
        requires_parent_condition_asset=False,
        parent_from_group_listing=True,
        expected_parent_id="6ef82585-fe7e-465c-a288-7a0463db6c5e",
        verify_content_readback=True,
    ),
)
