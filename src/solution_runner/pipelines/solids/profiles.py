"""Explicit category-three bindings for reviewed cube methods."""

from ..core.profile_definitions import _profile
from .box_profiles import PROFILES as BOX_PROFILES
from .box_section_profiles import PROFILES as SECTION_PROFILES
from .combined_profiles import PROFILES as COMBINED_PROFILES
from .cone_profiles import PROFILES as CONE_PROFILES
from .cylinder_profiles import PROFILES as CYLINDER_PROFILES
from .distance_profiles import PROFILES as DISTANCE_PROFILES
from .line_angle_profiles import PROFILES as LINE_ANGLE_PROFILES
from .orthogonal_profiles import PROFILES as ORTHOGONAL_PROFILES
from .polyhedron_profiles import PROFILES as POLYHEDRON_PROFILES
from .prism_profiles import PROFILES as PRISM_PROFILES
from .pyramid_profiles import PROFILES as PYRAMID_PROFILES
from .sphere_profiles import PROFILES as SPHERE_PROFILES
from .vertex_angle_profiles import PROFILES as VERTEX_ANGLE_PROFILES

PROFILES = tuple(
    _profile(
        key,
        uid,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="3",
        theme_title="Куб",
        theme_order_index=0,
        snapshot_theme_id="3489989a-cbeb-487d-a6c2-427548c7044e",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for key, uid, index, rule in (
        (
            "27056",
            "fb3806a5-38b0-4e7a-8bae-e68958101a7d",
            1,
            "solid-cube-surface-from-volume",
        ),
        (
            "27061",
            "91529fb4-4f38-47e9-95ed-7243646ad19d",
            2,
            "solid-cube-edge-from-surface-increase",
        ),
        (
            "27081",
            "37ca3a14-714d-4033-a9d3-cb5aa651afb5",
            3,
            "solid-cube-volume-factor",
        ),
        (
            "27098",
            "945c3a8a-3f55-4ed2-8fbf-e9206352e693",
            4,
            "solid-cube-volume-from-diagonal",
        ),
        (
            "27099",
            "0dc51aff-868d-44d8-bd74-fb80a3d084dd",
            5,
            "solid-cube-diagonal-from-volume",
        ),
        (
            "27102",
            "f73d2666-7612-4ab0-9126-98e3fca5671b",
            6,
            "solid-cube-edge-from-volume-increase",
        ),
        (
            "27130",
            "c413812b-07be-4ce3-8792-9f2c38b06d46",
            7,
            "solid-cube-surface-factor",
        ),
        (
            "27139",
            "db2aa44e-8105-449c-935b-1628e76b261c",
            8,
            "solid-cube-surface-from-diagonal",
        ),
        (
            "27141",
            "235f6e79-39c3-4f16-b00f-1eafc6e53b02",
            9,
            "solid-cube-volume-from-surface",
        ),
        (
            "27168",
            "33fd132a-a960-49c9-ac2f-99dd9ae407ba",
            10,
            "solid-cube-surface-factor-from-volume-factor",
        ),
        (
            "315130",
            "e00bbafa-87dd-477b-bbc8-5d235131879b",
            11,
            "solid-cube-midpoint-section-angle",
        ),
    )
)

PROFILES += (
    BOX_PROFILES + DISTANCE_PROFILES + LINE_ANGLE_PROFILES + VERTEX_ANGLE_PROFILES
)

PROFILES += POLYHEDRON_PROFILES + SECTION_PROFILES + SPHERE_PROFILES + CYLINDER_PROFILES

PROFILES += CONE_PROFILES

PROFILES += PRISM_PROFILES

PROFILES += PYRAMID_PROFILES

PROFILES += COMBINED_PROFILES

PROFILES += ORTHOGONAL_PROFILES
