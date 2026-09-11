from solution_runner.dashboard.teacherhelper import teacherhelper_navigation
from solution_runner.pipelines.core.group_profiles import get_group_profile


def test_teacherhelper_navigation_uses_source_site_from_the_same_catalog():
    assert teacherhelper_navigation(get_group_profile("26656")) == {
        "source_site_id": "4e79360f-d623-4d50-9e85-67858ac1bc85",
        "snapshot_id": "41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        "category_id": "9c34b1ea-0cb8-4dc9-a841-3956f290d786",
        "theme_id": "f598f433-d5cf-4ca7-af95-0d1cb6b52818",
        "group_id": "940a61ed-f4c1-4dee-b1f2-4bf7b256f254",
    }
    assert teacherhelper_navigation(get_group_profile("315122")) == {
        "source_site_id": "7bed2492-5b8b-4c88-9be8-7d47916cd7c6",
        "snapshot_id": "4073fc7b-2056-4697-b18b-38741c94d0f4",
        "category_id": "a0de34d5-e097-4ea9-aabb-eeb2a9f10187",
        "theme_id": "d50df164-ea7e-4058-a5b5-8d665c586cf3",
        "group_id": "e94045ee-a79e-4424-a8ae-81a775008a79",
    }
    assert teacherhelper_navigation(get_group_profile("323750")) == {
        "source_site_id": "9b8fb96a-649b-494b-afa5-ecdd9a7dca5e",
        "snapshot_id": "fd733f80-43d2-4b4a-b903-2423796cbee5",
        "category_id": "0810de1a-a670-48d7-80b2-e2c585e6675b",
        "theme_id": "58adee76-92b1-4e53-9ad2-e89d0129d238",
        "group_id": "97baf536-473e-4a52-89f0-b92a420ebfca",
    }
