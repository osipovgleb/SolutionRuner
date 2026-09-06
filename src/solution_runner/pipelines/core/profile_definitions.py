"""Shared source identifiers and immutable group-profile constructor."""

from __future__ import annotations

from .models import GroupProfile


CATALOG_SNAPSHOT_ID = "4073fc7b-2056-4697-b18b-38741c94d0f4"
TRAPEZOID_THEME_ID = "26af5056-7c19-4148-85a2-ce95069d8760"
TRIANGLE_THEME_ID = "3913765c-3750-456e-aaff-2fc050bc8821"
RHOMBUS_THEME_ID = "785f5813-b3f0-41cd-b6a1-6c63c4223d5e"
ARBITRARY_QUADRILATERAL_THEME_ID = "3bfd66e9-836c-4eda-a293-9885053ec4bd"
OGE_CATALOG_SNAPSHOT_ID = "fd733f80-43d2-4b4a-b903-2423796cbee5"
OGE_AREAS_THEME_ID = "58adee76-92b1-4e53-9ad2-e89d0129d238"
CIRCLE_THEME_ID = "d50df164-ea7e-4058-a5b5-8d665c586cf3"


def _profile(
    group_key: str,
    source_group_id: str,
    group_order_index: int,
    **options: object,
) -> GroupProfile:
    """Build one validated immutable group profile from audited constants."""

    rewrite_existing_solution = bool(options.pop("rewrite_existing_solution", False))
    catalog_snapshot_id = str(options.pop("catalog_snapshot_id", CATALOG_SNAPSHOT_ID))
    return GroupProfile(
        catalog_snapshot_id=catalog_snapshot_id,
        source_group_id=source_group_id,
        group_key=group_key,
        group_order_index=group_order_index,
        existing_solution_policy=(
            "rewrite" if rewrite_existing_solution else "preserve"
        ),
        **options,
    )
