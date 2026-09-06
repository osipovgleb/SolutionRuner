"""Shared deterministic content-planning failure."""


class ContentPlanError(ValueError):
    """A condition or execution input is outside the safe runner contract."""
