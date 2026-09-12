"""Expose immutable reusable solution-strategy selection."""

from __future__ import annotations

from types import MappingProxyType

from ..models import StrategyKey
from .base_height_triangle import BaseHeightTriangleStrategy
from .annulus_area import AnnulusAreaStrategy
from .annulus_from_known_area import AnnulusFromKnownAreaStrategy
from .bounding_rectangle_quadrilateral import BoundingRectangleQuadrilateralStrategy
from .bounding_rectangle_triangle import BoundingRectangleTriangleStrategy
from .bounding_rectangle_trapezoid import BoundingRectangleTrapezoidStrategy, TrapezoidPickStrategy
from .grid_cell_count import GridCellCountStrategy
from .parallel_bases_trapezoid import ParallelBasesTrapezoidStrategy, ParallelBasesTrapezoidThreeMethodsStrategy
from .parallelogram_three_methods import ParallelogramThreeMethodsStrategy
from .protocol import SolutionStrategy
from .right_triangle import RightTriangleStrategy


_STRATEGIES = MappingProxyType(
    {
        strategy.key: strategy
        for strategy in (
            AnnulusAreaStrategy(),
            AnnulusFromKnownAreaStrategy(),
            RightTriangleStrategy(),
            BaseHeightTriangleStrategy(),
            BoundingRectangleQuadrilateralStrategy(),
            BoundingRectangleTriangleStrategy(),
            ParallelBasesTrapezoidStrategy(),
            ParallelBasesTrapezoidThreeMethodsStrategy(),
            ParallelogramThreeMethodsStrategy(),
            BoundingRectangleTrapezoidStrategy(),
            TrapezoidPickStrategy(),
            GridCellCountStrategy(),
        )
    }
)


def get_solution_strategy(key: StrategyKey) -> SolutionStrategy:
    """Return one explicit pure strategy or fail before any runtime write."""

    try:
        return _STRATEGIES[key]
    except KeyError as exc:
        raise KeyError(f"unsupported solution strategy: {key}") from exc
