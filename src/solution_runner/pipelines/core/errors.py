"""Shared deterministic content-planning failure."""


class ContentPlanError(ValueError):
    """A condition or execution input is outside the safe runner contract."""


class InvalidInputType(TypeError, ValueError):
    """Indicate an invalid input type while retaining ValueError compatibility."""
