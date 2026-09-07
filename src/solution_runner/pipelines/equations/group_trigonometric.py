"""Registered fail-closed entry point for tabular trigonometric equations.

The complete behavioural contract is in ``docs/trigonometric-equations-runner.md``.
No task can be changed until its accepted value has both a reviewed static SVG
and parser regression coverage.
"""

from __future__ import annotations

from typing import Any


RULE = "trigonometric-table-value-affine-argument"


class UnsupportedCondition(ValueError):
    """Reject unimplemented or ambiguous trigonometric task shapes safely."""


def build_context_repair_plan(context: dict[str, Any]):
    """Reserve the shared runner entry point while asset/value matrix is prepared.

    The registration is intentionally live so profile/handler wiring is checked
    by the normal registry suite.  The planner is deliberately fail-closed until
    the reviewed static SVG matrix and exact tabular-value corpus are committed.
    """

    del context
    raise UnsupportedCondition(
        "trigonometric runner is registered; approved value/SVG matrix is pending"
    )
