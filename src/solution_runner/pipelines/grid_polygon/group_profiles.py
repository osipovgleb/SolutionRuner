"""Compatibility exports for definitions moved to the domain-neutral core."""

from solution_runner.pipelines.core.group_profiles import (
    ARBITRARY_QUADRILATERAL_THEME_ID,
    CATALOG_SNAPSHOT_ID,
    CIRCLE_THEME_ID,
    OGE_AREAS_THEME_ID,
    OGE_CATALOG_SNAPSHOT_ID,
    RHOMBUS_THEME_ID,
    TRAPEZOID_THEME_ID,
    TRIANGLE_THEME_ID,
    GroupProfile,
    all_group_profiles,
    build_profile_registry,
    get_group_profile,
    reload_group_profiles,
)

__all__ = [
    "ARBITRARY_QUADRILATERAL_THEME_ID",
    "CATALOG_SNAPSHOT_ID",
    "CIRCLE_THEME_ID",
    "OGE_AREAS_THEME_ID",
    "OGE_CATALOG_SNAPSHOT_ID",
    "RHOMBUS_THEME_ID",
    "TRAPEZOID_THEME_ID",
    "TRIANGLE_THEME_ID",
    "GroupProfile",
    "all_group_profiles",
    "build_profile_registry",
    "get_group_profile",
    "reload_group_profiles",
]
