"""Shared error and repair-plan types for isosceles triangle rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class IsoscelesTrianglePlanError(ValueError):
    """Report an unsupported or inconsistent isosceles-triangle task."""


@dataclass(frozen=True)
class RepairPlan:
    """Carry one exact answer and the transformations needed to reach it."""

    answer: str
    transformations: tuple[dict[str, Any], ...]
