"""Validated aggregate of domain-owned group declarations."""
from types import MappingProxyType
from typing import Mapping
from .models import GroupProfile
from .handler_registry import get_handler
from .profile_definitions import (
    CATALOG_SNAPSHOT_ID,
    TRAPEZOID_THEME_ID,
    TRIANGLE_THEME_ID,
    RHOMBUS_THEME_ID,
    ARBITRARY_QUADRILATERAL_THEME_ID,
    OGE_CATALOG_SNAPSHOT_ID,
    OGE_AREAS_THEME_ID,
    CIRCLE_THEME_ID,
)
from solution_runner.pipelines.equations.profiles import PROFILES as EQUATIONS
from solution_runner.pipelines.vectors.profiles import PROFILES as VECTORS
from solution_runner.pipelines.triangles.general.profiles import PROFILES as TRIANGLES_GENERAL
from solution_runner.pipelines.quadrilaterals.parallelogram.profiles import PROFILES as QUADRILATERALS_PARALLELOGRAM
from solution_runner.pipelines.quadrilaterals.trapezoid.profiles import PROFILES as QUADRILATERALS_TRAPEZOID
from solution_runner.pipelines.triangles.isosceles.profiles import PROFILES as TRIANGLES_ISOSCELES
from solution_runner.pipelines.triangles.right.profiles import PROFILES as TRIANGLES_RIGHT
from solution_runner.pipelines.grid_polygon.profiles import PROFILES as GRID_POLYGON
from solution_runner.pipelines.word_problems.profiles import PROFILES as WORD_PROBLEMS


def build_profile_registry(profiles) -> Mapping[str, GroupProfile]:
    result = {}
    for profile in profiles:
        if profile.group_key in result:
            raise ValueError(f"duplicate group key: {profile.group_key}")
        if profile.workflow_kind == "content_rule":
            get_handler(profile.content_rule_key)
        result[profile.group_key] = profile
    return MappingProxyType(result)


_PROFILES = build_profile_registry((*EQUATIONS, *VECTORS, *TRIANGLES_GENERAL, *QUADRILATERALS_PARALLELOGRAM, *QUADRILATERALS_TRAPEZOID, *TRIANGLES_ISOSCELES, *TRIANGLES_RIGHT, *GRID_POLYGON, *WORD_PROBLEMS))


def get_group_profile(group_key: str) -> GroupProfile:
    try:
        profile = _PROFILES[group_key]
    except KeyError as exc:
        raise KeyError(f"unsupported group: {group_key}") from exc
    if profile.workflow_kind == "content_rule":
        get_handler(profile.content_rule_key).validate()
    return profile


def all_group_profiles() -> Mapping[str, GroupProfile]:
    return _PROFILES
