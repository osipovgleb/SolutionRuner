"""One lookup table for content rules from all mathematical domains."""

from importlib import import_module, reload
from types import MappingProxyType

from solution_runner.pipelines.equations.handlers import HANDLERS as EQUATIONS
from solution_runner.pipelines.function_graphs.handlers import (
    HANDLERS as FUNCTION_GRAPHS,
)
from solution_runner.pipelines.informatics.handlers import HANDLERS as INFORMATICS
from solution_runner.pipelines.probability.handlers import HANDLERS as PROBABILITY
from solution_runner.pipelines.quadrilaterals.parallelogram.handlers import (
    HANDLERS as PARALLELOGRAMS,
)
from solution_runner.pipelines.quadrilaterals.trapezoid.handlers import (
    HANDLERS as TRAPEZOIDS,
)
from solution_runner.pipelines.statistics.handlers import HANDLERS as STATISTICS
from solution_runner.pipelines.triangles.general.handlers import (
    HANDLERS as GENERAL_TRIANGLES,
)
from solution_runner.pipelines.triangles.isosceles.handlers import (
    HANDLERS as ISOSCELES_TRIANGLES,
)
from solution_runner.pipelines.triangles.right.handlers import (
    HANDLERS as RIGHT_TRIANGLES,
)
from solution_runner.pipelines.vectors.handlers import HANDLERS as VECTORS
from solution_runner.pipelines.word_problems.handlers import HANDLERS as WORD_PROBLEMS

from .handlers import HandlerSpec


def build_registry(specs):
    result = {}
    for spec in specs:
        if spec.key in result:
            raise ValueError(f"duplicate handler key: {spec.key}")
        result[spec.key] = spec
    return MappingProxyType(result)


HANDLERS = build_registry(
    (
        *EQUATIONS,
        *FUNCTION_GRAPHS,
        *GENERAL_TRIANGLES,
        *ISOSCELES_TRIANGLES,
        *PARALLELOGRAMS,
        *RIGHT_TRIANGLES,
        *TRAPEZOIDS,
        *VECTORS,
        *WORD_PROBLEMS,
        *INFORMATICS,
        *PROBABILITY,
        *STATISTICS,
    )
)


def get_handler(key: str) -> HandlerSpec:
    try:
        return HANDLERS[key]
    except KeyError as exc:
        raise KeyError(f"unsupported content rule: {key}") from exc


def reload_handler_registry():
    """Refresh domain declarations before validating newly registered profiles."""
    global HANDLERS
    modules = (
        "equations",
        "function_graphs",
        "triangles.general",
        "triangles.isosceles",
        "quadrilaterals.parallelogram",
        "triangles.right",
        "quadrilaterals.trapezoid",
        "vectors",
        "word_problems",
        "informatics",
        "probability",
        "statistics",
    )
    HANDLERS = build_registry(
        spec
        for domain in modules
        for spec in reload(
            import_module(f"solution_runner.pipelines.{domain}.handlers")
        ).HANDLERS
    )
    return HANDLERS
