"""Validated aggregate of domain-owned group declarations."""
from importlib import import_module, invalidate_caches, reload
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


_PROFILE_MODULES = (
    "solution_runner.pipelines.equations.profiles",
    "solution_runner.pipelines.function_graphs.profiles",
    "solution_runner.pipelines.vectors.profiles",
    "solution_runner.pipelines.triangles.general.profiles",
    "solution_runner.pipelines.quadrilaterals.parallelogram.profiles",
    "solution_runner.pipelines.quadrilaterals.trapezoid.profiles",
    "solution_runner.pipelines.triangles.isosceles.profiles",
    "solution_runner.pipelines.triangles.right.profiles",
    "solution_runner.pipelines.grid_polygon.profiles",
    "solution_runner.pipelines.word_problems.profiles",
)


def build_profile_registry(profiles) -> Mapping[str, GroupProfile]:
    result = {}
    for profile in profiles:
        if profile.group_key in result:
            raise ValueError(f"duplicate group key: {profile.group_key}")
        if profile.workflow_kind == "content_rule":
            get_handler(profile.content_rule_key)
        result[profile.group_key] = profile
    return MappingProxyType(result)


def _build_profiles() -> Mapping[str, GroupProfile]:
    return build_profile_registry(tuple(
        profile
        for module_name in _PROFILE_MODULES
        for profile in import_module(module_name).PROFILES
    ))


_PROFILES = _build_profiles()


def reload_group_profiles() -> Mapping[str, GroupProfile]:
    """Reload declarations written by a registration task without restarting callers."""

    global _PROFILES
    invalidate_caches()
    for module_name in _PROFILE_MODULES:
        reload(import_module(module_name))
    _PROFILES = _build_profiles()
    return _PROFILES


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
