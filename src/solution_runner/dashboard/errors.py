"""Errors raised while validating data consumed by the dashboard."""


class InvalidPayloadType(TypeError, ValueError):
    """Report a malformed payload while preserving existing ValueError handlers."""
