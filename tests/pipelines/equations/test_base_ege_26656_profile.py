"""Registration coverage for the base-EGE irrational-equation group."""

from solution_runner.pipelines.core.group_profiles import get_group_profile


def test_base_ege_group_26656_reuses_the_square_root_affine_handler() -> None:
    profile = get_group_profile("ege-base-26656")

    assert profile.source_group_id == "9d40658b-7204-4454-ae72-4b4cba945e2a"
    assert profile.content_rule_key == "irrational-26656-square-root-affine"


def test_base_ege_group_27465_reuses_the_square_root_affine_handler() -> None:
    profile = get_group_profile("ege-base-27465")

    assert profile.source_group_id == "77164c04-d289-4380-800d-03ccbf3f8894"
    assert profile.content_rule_key == "irrational-26656-square-root-affine"


def test_base_ege_group_500907_reuses_the_square_root_affine_handler() -> None:
    profile = get_group_profile("ege-base-500907")

    assert profile.source_group_id == "d73b3256-cf63-4f96-838f-f766b18d1ced"
    assert profile.content_rule_key == "irrational-26656-square-root-affine"


def test_base_ege_group_511751_uses_reciprocal_square_root_handler() -> None:
    profile = get_group_profile("ege-base-511751")

    assert profile.source_group_id == "b3f00718-2a5d-436b-9d2c-2afe624fa39b"
    assert profile.content_rule_key == "irrational-511751-reciprocal-square-root"
