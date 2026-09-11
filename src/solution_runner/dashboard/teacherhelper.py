"""Build TeacherHelper navigation data for registered source groups."""

from __future__ import annotations

from typing import Any

from solution_runner.pipelines.grid_polygon.mcp_runtime import SOURCE_SITE_ID


CATEGORY_IDS = {
    ("4073fc7b-2056-4697-b18b-38741c94d0f4", "1"): "c226053c-29e7-4e88-aafb-81896ab0d969",
    ("4073fc7b-2056-4697-b18b-38741c94d0f4", "9"): "651e7b69-ab21-4d51-9115-7491e0a7f2c9",
    ("4073fc7b-2056-4697-b18b-38741c94d0f4", "12"): "a0de34d5-e097-4ea9-aabb-eeb2a9f10187",
    ("4073fc7b-2056-4697-b18b-38741c94d0f4", "14"): "3b936b30-20a4-4793-af65-5a289eb1fa40",
    ("4073fc7b-2056-4697-b18b-38741c94d0f4", "17"): "6c524e89-b52c-4ef4-873a-1fe6598dd4ef",
    ("41bc4d03-40cd-4407-8dea-df76e3f47ea8", "1"): "0255b2f6-ef48-4356-8edf-aec792deb65b",
    ("41bc4d03-40cd-4407-8dea-df76e3f47ea8", "2"): "3df2f927-25a9-47b9-8fae-a92dec6005d0",
    ("41bc4d03-40cd-4407-8dea-df76e3f47ea8", "7"): "9c34b1ea-0cb8-4dc9-a841-3956f290d786",
    ("41bc4d03-40cd-4407-8dea-df76e3f47ea8", "8"): "a912fdaf-5f28-47ac-98fe-78af415e3e43",
    ("41bc4d03-40cd-4407-8dea-df76e3f47ea8", "11"): "90f1e24c-7179-461a-8b32-8da19760befb",
    ("fd733f80-43d2-4b4a-b903-2423796cbee5", "6"): "9aa43047-42c9-44e7-8944-6b9d225745bd",
    ("fd733f80-43d2-4b4a-b903-2423796cbee5", "8"): "4f341dd8-08a3-4250-bcca-202b008c7e25",
    ("fd733f80-43d2-4b4a-b903-2423796cbee5", "18"): "0810de1a-a670-48d7-80b2-e2c585e6675b",
}


def teacherhelper_navigation(profile: Any) -> dict[str, str] | None:
    snapshot_id = str(profile.catalog_snapshot_id)
    category_id = CATEGORY_IDS.get((snapshot_id, str(profile.category_key)))
    if category_id is None:
        return None
    return {
        "source_site_id": SOURCE_SITE_ID,
        "snapshot_id": snapshot_id,
        "category_id": category_id,
        "theme_id": str(profile.snapshot_theme_id),
        "group_id": str(profile.source_group_id),
    }
