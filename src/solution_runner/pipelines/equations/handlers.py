"""Ordered handler declarations for the equations domain."""

from .exam_equation_handlers import HANDLERS as _EXAM_EQUATION_HANDLERS
from .exam_extended_inequality_handlers import (
    HANDLERS as _EXAM_EXTENDED_INEQUALITY_HANDLERS,
)
from .exam_initial_log_handlers import HANDLERS as _EXAM_INITIAL_LOG_HANDLERS
from .exam_rational_exponential_handlers import (
    HANDLERS as _EXAM_RATIONAL_EXPONENTIAL_HANDLERS,
)
from .foundation_handlers import HANDLERS as _FOUNDATION_HANDLERS
from .numeric_handlers import HANDLERS as _NUMERIC_HANDLERS

HANDLERS = (
    _FOUNDATION_HANDLERS
    + _NUMERIC_HANDLERS
    + _EXAM_EQUATION_HANDLERS
    + _EXAM_INITIAL_LOG_HANDLERS
    + _EXAM_RATIONAL_EXPONENTIAL_HANDLERS
    + _EXAM_EXTENDED_INEQUALITY_HANDLERS
)
