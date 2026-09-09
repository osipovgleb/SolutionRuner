"""One lookup table for content rules from all mathematical domains."""
from types import MappingProxyType
from .handlers import HandlerSpec
from solution_runner.pipelines.equations.handlers import HANDLERS as EQUATIONS
from solution_runner.pipelines.triangles.general.handlers import HANDLERS as GENERAL_TRIANGLES
from solution_runner.pipelines.triangles.isosceles.handlers import HANDLERS as ISOSCELES_TRIANGLES
from solution_runner.pipelines.quadrilaterals.parallelogram.handlers import HANDLERS as PARALLELOGRAMS
from solution_runner.pipelines.triangles.right.handlers import HANDLERS as RIGHT_TRIANGLES
from solution_runner.pipelines.quadrilaterals.trapezoid.handlers import HANDLERS as TRAPEZOIDS
from solution_runner.pipelines.vectors.handlers import HANDLERS as VECTORS
from solution_runner.pipelines.word_problems.handlers import HANDLERS as WORD_PROBLEMS


def build_registry(specs):
    result = {}
    for spec in specs:
        if spec.key in result:
            raise ValueError(f"duplicate handler key: {spec.key}")
        result[spec.key] = spec
    return MappingProxyType(result)


HANDLERS = build_registry((
    *EQUATIONS, *GENERAL_TRIANGLES, *ISOSCELES_TRIANGLES, *PARALLELOGRAMS,
    *RIGHT_TRIANGLES, *TRAPEZOIDS, *VECTORS, *WORD_PROBLEMS,
))


def get_handler(key: str) -> HandlerSpec:
    try:
        return HANDLERS[key]
    except KeyError as exc:
        raise KeyError(f"unsupported content rule: {key}") from exc
