"""Protect explicit group-to-strategy configuration without executable globals."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from solution_runner.pipelines.grid_polygon.group_profiles import (
    all_group_profiles,
    get_group_profile,
)


EXPECTED_GROUPS = {
    "27284": ("6fa6e46a-8e66-40ab-8b12-a830d8cec6fe", None, None),
    "27285": ("e815ef19-e5b1-4407-bcb3-011d096b8f46", None, None),
    "27286": ("3a9411cf-7a1f-47dc-bbce-c93b5fb195f9", None, None),
    "27287": ("a727f9dc-6b5a-49dd-bb74-31f8b835345c", None, None),
    "27288": ("482de95f-6205-4cfd-878f-88227eb501aa", None, None),
    "27289": ("33d2d058-f5e9-49cf-b83d-df0e22c0482e", None, None),
    "27320": ("5f905ca1-bfc0-4546-95ac-72c0f22f5284", None, None),
    "27321": ("ef239149-1b92-4573-a60e-e38bc6c3856d", None, None),
    "27322": ("b6d48b45-2b2e-4851-ac2b-a3fff514d11c", None, None),
    "27323": ("9d9192f0-dabf-4f7d-9665-8e8a05bbdd00", None, None),
    "27324": ("263cee7b-84b2-419b-b477-cc0875eeb64c", None, None),
    "27325": ("5917071a-fc81-4320-8202-af2e7f468420", None, None),
    "27326": ("cc8ac9bd-38d9-4e19-a5d0-78b10dad0a08", None, None),
    "27327": ("9a8a2548-ffaa-4bb9-a724-e671bd383578", None, None),
    "27328": ("56418c18-4e1f-4451-ae9e-ee6d69abde6b", None, None),
    "27329": ("16b0a5e8-4a82-40f8-ab51-06ffd1143ec4", None, None),
    "27330": ("e3095238-d81c-4960-abdc-8ff61d888ce9", None, None),
    "27331": ("ed3ab9cf-7727-46a6-ab23-dff81576e978", None, None),
    "27345": ("24fc66f3-5d60-4c2d-b1e9-8ab0972f0706", None, None),
    "27346": ("26dc4edc-cb5a-4535-88e3-d7578137a1e8", None, None),
    "27347": ("e3aaf0a9-a86b-4258-969a-22021cce96ac", None, None),
    "27349": ("93bfccca-3825-4643-b772-9f2d72815859", None, None),
    "27350": ("f6e782e8-8150-4dd2-b2a0-c2b0937d4f9e", None, None),
    "27351": ("58965e04-a2e5-439d-8d46-9c332e6feda8", None, None),
    "27352": ("521961e3-c80d-4159-9592-54715f378e01", None, None),
    "27353": ("a5396206-e4a2-4240-b9f8-d10b511aaf8f", None, None),
    "27589": ("20eda0b6-a707-4153-9b6b-5df327c5a202", None, None),
    "27590": ("deee0c98-c0ca-4f12-9c76-6701db6689be", None, None),
    "27619": ("9b7663e9-43fd-45e4-9b3d-e705889d0b8f", None, None),
    "27620": ("512d33b1-096c-41d2-b501-436fdef5c609", None, None),
    "27621": ("8ff6e871-7bfd-4089-aba4-ed8ef272a15d", None, None),
    "27744": ("4bab2693-5943-4e73-883d-5a894b06ff0f", None, None),
    "27745": ("eba7ce04-ab23-415d-8241-423bbc4b8532", None, None),
    "27746": ("4e911c5a-5544-4652-80bc-de48d31b1a3c", None, None),
    "27747": ("3abe67c2-dfd4-46d3-bcd9-c6c8773305e2", None, None),
    "27748": ("eb180ea5-3b90-4ff9-aadb-f650e7a1ddfd", None, None),
    "27750": ("baf6a113-1ccb-4d8a-8f5d-156c8c2c619a", None, None),
    "27754": ("71164990-d7a9-4b4a-af7f-f7757bb539a5", None, None),
    "27760": ("fdb7d393-9db5-4783-be35-f92580fb4dfe", None, None),
    "27792": ("a9f89380-21ba-4140-8e96-6c6b9fda5e69", None, None),
    "27793": ("6c69bf93-b48a-4926-90f5-ff6e90713b17", None, None),
    "27794": ("81397f25-4a49-480e-8df6-4608c6bc0241", None, None),
    "27795": ("ad9ec64f-e251-416d-b139-ec1d3c70c17f", None, None),
    "27796": ("5931b6b0-f716-4c2c-a3ef-104994717cd9", None, None),
    "27797": ("e2f29aea-314d-4db8-856e-132a4d8d9203", None, None),
    "27798": ("beb59dd9-6f89-468a-ae74-9d90588781fb", None, None),
    "27799": ("b69438ac-93e6-49e5-a4a8-4cd48c1fdd1d", None, None),
    "27800": ("4e16550e-63d7-4415-9c21-1c3eee965acb", None, None),
    "628232": ("bfd0cec1-867f-4ffa-a94a-515959de6a5e", None, None),
    "676342": ("983f0386-50d8-4c27-bd3d-736d0f587828", None, None),
    "701874": ("5c464e32-f6fc-4323-8658-1eeaac157299", None, None),
    "27238": ("8b5a2cb7-4831-4355-9d47-e473b8aef65c", None, None),
    "27239": ("d7569951-414e-4d7e-85d0-6f5509fc116f", None, None),
    "27240": ("9333c06b-a69d-49be-81d0-297a0e6bc194", None, None),
    "27243": ("f8e433ab-6dc0-41fc-9841-6de9135566c4", None, None),
    "27242": ("127bf3ef-3eff-47b2-b77c-87dc842421bb", None, None),
    "27244": ("fa52d73f-7f5b-44c8-a592-46efff4db916", None, None),
    "27247": ("5a4134a0-4cbc-423d-896c-18154a429dce", None, None),
    "27249": ("52ebad7f-0bd7-4663-8b9c-35331a27b143", None, None),
    "27250": ("1b65c948-4216-4182-951d-4da316235480", None, None),
    "27265": ("23402d00-846a-4db5-9103-a956e244203e", None, None),
    "27266": ("e377cf2d-ded2-46d2-9c54-094d768f47a2", None, None),
    "27267": ("a3245268-b5fc-4912-9066-f387cb9c5327", None, None),
    "27268": ("85c32d94-6bcd-485d-8c81-000e8a8953be", None, None),
    "27269": ("598b542c-547a-40b4-9b5c-7f1ebf063585", None, None),
    "27270": ("fccb7e66-6f5f-425d-b013-20a28bc18dad", None, None),
    "27271": ("07b024c7-a4a9-42da-8f06-3b76c754d39a", None, None),
    "27272": ("db056adf-8ca1-490c-8a55-6e87b956a97e", None, None),
    "27273": ("779b4486-f7f0-412d-9e71-20e2703a5c64", None, None),
    "27280": ("068762af-3edb-4a5b-9b14-b3f8dbce0dec", None, None),
    "27336": ("1c9d01cd-3ae5-4624-b97a-802f483b09d2", None, None),
    "27337": ("80f2d73c-52e9-44cc-97db-4657d0c3cc74", None, None),
    "27338": ("10c54900-a29d-471a-bd8c-9a42b59fb6e2", None, None),
    "27339": ("369efb41-a0bc-4ac3-be7b-8b485c357f40", None, None),
    "27340": ("d3c7e2f9-65e0-427f-b4d9-2d4874de0de3", None, None),
    "27341": ("7760fde3-96e2-4f14-ba95-3fd58bbfe22e", None, None),
    "27342": ("6404ea88-a14c-4e8c-a5df-60820dbd0a02", None, None),
    "27343": ("0688995b-5e9c-4098-bc97-5fc541d5bdf2", None, None),
    "27344": ("dfe23c14-0758-49bf-adbe-b0fe8578018b", None, None),
    "27357": ("3a320928-1a84-4c55-ae7a-69ce25882da6", None, None),
    "27358": ("b0095bf0-f6ce-4742-afd4-e8e172e452c6", None, None),
    "27431": ("4b93b53e-bd57-4033-8213-a6201f5151bc", None, None),
    "27432": ("da3ae05d-953c-4f39-b85a-7e4466ef499c", None, None),
    "27617": ("96477e5e-4194-4211-95ba-683876577f4f", None, None),
    "27618": ("3d399961-7f2c-4c8f-a97d-69ec6df8d19b", None, None),
    "27742": ("6bb5c896-1064-4510-bd34-9b625ae544fa", None, None),
    "27753": ("1cb9af83-8463-44ba-a407-de890b23e646", None, None),
    "27761": ("da62a5ad-58f1-482e-b597-fa9b3ce0d9de", None, None),
    "27765": ("07ff93c8-7436-49d5-9970-c471131e5e69", None, None),
    "27770": ("8cda3670-eb2b-47f6-aee2-87a18fc33a15", None, None),
    "27771": ("3ad3751b-dbcd-409f-85bc-bba308a09fde", None, None),
    "27772": ("98f0e947-9327-4d19-b09b-a91dc805114e", None, None),
    "27773": ("34a912a3-be54-40ee-82c5-b1f595afba5a", None, None),
    "27774": ("c519d5ac-8460-4fe4-82dd-39a6f89236c6", None, None),
    "27775": ("228ba65b-e3bb-42f4-a79c-e38be708cc6d", None, None),
    "27789": ("be74920f-7317-46b2-90f7-91f4b05b43b2", None, None),
    "27790": ("d1a1906b-4407-4824-ae72-78bb95e7ecd9", None, None),
    "27791": ("e731573a-c95b-4cc4-bfd6-dab7432d0a1c", None, None),
    "27556": ("fc5fc7a7-75ba-41d4-9bb7-4fee7b1b8be1", "parallel-bases-trapezoid", 4),
    "27557": ("ae4b8e1f-4ff2-4085-aee5-d3be39ccdbd6", "parallel-bases-trapezoid", 4),
    "27558": ("416046da-eecc-4473-83fd-b1b6c799a7e6", "parallel-bases-trapezoid", 4),
    "27559": ("0719750c-08ff-450c-bc16-3a65989caf9a", "parallel-bases-trapezoid", 4),
    "27560": ("3fb2e89d-9858-4c76-9683-d2d348ce4a35", "parallel-bases-trapezoid", 4),
    "244985": ("f2422780-bacb-4231-a06a-b89e855fc801", "bounding-rectangle-trapezoid", 4),
    "244986": ("0be1e4bb-4e88-43d0-8f03-2d4b1440773c", "bounding-rectangle-trapezoid", 4),
    "27543": ("4808d0b7-aa63-4a5f-85ed-da28c8f80b18", "right-triangle", 3),
    "27544": ("b8fcbdc6-7967-4bc0-99b1-3fa49d5d824f", "base-height-triangle", 3),
    "27545": ("0d938f6c-b012-4013-8dad-778add652e11", "base-height-triangle", 3),
    "27546": ("d371408f-f616-4ed0-9cea-85f27fc30c4e", "base-height-triangle", 3),
    "27547": ("96309f98-73c1-4abc-8005-73a4307e7295", "base-height-triangle", 3),
    "27548": ("7e1ba8c1-23dc-4e04-aec2-67e23ef52cc7", "bounding-rectangle-triangle", 3),
    "27549": ("3e818284-d58c-43a6-b7b4-c21a48e5a425", "bounding-rectangle-triangle", 3),
    "244982": ("a3e9590e-400a-4e2e-9fcc-a4ddc94e53ab", "bounding-rectangle-triangle", 3),
    "244983": ("c7fb645b-bb12-48f9-86c9-de6bd980389e", "bounding-rectangle-quadrilateral", 4),
    "27553": ("0efa9c9d-8b0a-4eda-8f91-3bab53034f85", "bounding-rectangle-quadrilateral", 4),
    "27554": ("8692d319-27c2-4e8b-994a-6efa20a7adac", "bounding-rectangle-quadrilateral", 4),
    "27555": ("e779214c-ef69-400f-9516-db1e3cec409d", "bounding-rectangle-quadrilateral", 4),
    "244987": ("65378636-e6f5-4087-8d36-37bf60e01556", "bounding-rectangle-quadrilateral", 4),
    "244988": ("21f4102f-5758-4069-8ade-e35d3c1a91e4", "bounding-rectangle-quadrilateral", 4),
    "244989": ("07db163e-8cb4-4fb9-abda-11ea84c72697", "bounding-rectangle-quadrilateral", 4),
    "244990": ("c1720bed-72fd-4c28-8cc8-ab67cbab3449", "bounding-rectangle-quadrilateral", 4),
    "244991": ("500815ad-983f-4658-820c-e63a4c3ca08e", "bounding-rectangle-quadrilateral", 4),
    "244992": ("dfbc0d00-a0ee-4e3e-8791-369cf64339cc", "bounding-rectangle-quadrilateral", 4),
    "244993": ("482c8645-573c-4d09-962a-10f9347e346a", "bounding-rectangle-quadrilateral", 4),
    "244994": ("4af236f2-0dc6-44d1-b99e-d604fbe803b3", "bounding-rectangle-quadrilateral", 4),
    "244995": ("1de2d522-204a-439e-99c1-37eb45881192", "bounding-rectangle-quadrilateral", 4),
    "244996": ("07793db5-7983-4a49-81fc-2a1c04a21599", "bounding-rectangle-quadrilateral", 4),
    "244997": ("c311c7ee-6156-4164-b052-dee139e6feb4", "bounding-rectangle-quadrilateral", 4),
    "244998": ("a56949ab-bcc3-409d-8375-a216927ed92a", "bounding-rectangle-quadrilateral", 4),
    "244999": ("a6c625ec-3b46-48ff-a1d5-a4518995a144", "bounding-rectangle-quadrilateral", 4),
    "245000": ("d4f8b1b5-4a4f-4cca-9523-fcd32ac1e8f0", "bounding-rectangle-quadrilateral", 4),
    "245001": ("8fa38806-4fb0-45d2-98e8-da85dc47ff1b", "bounding-rectangle-quadrilateral", 4),
    "245002": ("07702ba0-2f65-4693-a842-cf44c1a0b194", "bounding-rectangle-quadrilateral", 4),
    "245003": ("d0d1abe1-9b69-479d-8f43-b6f9182e861f", "bounding-rectangle-quadrilateral", 4),
    "245004": ("5934b527-a4dc-49aa-95c5-4e748661b4f2", "bounding-rectangle-quadrilateral", 4),
    "245006": ("186ffd8e-c830-476e-8361-98e8ba5dadf8", "bounding-rectangle-quadrilateral", 4),
    "245007": ("2d78a6aa-7d44-4509-ac8e-534dc0a59349", "bounding-rectangle-quadrilateral", 4),
    "323750": ("97baf536-473e-4a52-89f0-b92a420ebfca", "bounding-rectangle-quadrilateral", 4),
    "323790": ("ff1e58f4-d569-434a-bfd1-b4a31e75782d", "bounding-rectangle-quadrilateral", 4),
    "341675": ("2b066b10-da4a-43bc-b287-7d3d5e4ec7fc", "grid-cell-count", None),
    "348403": ("b3c35c7f-6c8f-4850-adf2-ef85a36fb60a", "base-height-triangle", 3),
    "348499": (
        "ba2d7dc4-f2e2-49ab-b583-499866c5e1dd",
        "parallelogram-three-methods",
        4,
    ),
    "245008": ("35a2b971-d6d3-4013-817b-5dd44a4e9c65", "annulus-area", None),
    "315122": ("e94045ee-a79e-4424-a8ae-81a775008a79", "annulus-from-known-area", None),
    "315123": ("4284ccf4-35a4-4eb8-827c-15ca5577ed6c", "annulus-from-known-area", None),
    "315124": ("29279769-bf35-43de-b72a-5ccfab6f0932", "annulus-from-known-area", None),
}


def test_group_27284_uses_its_strict_isosceles_rule() -> None:
    """Keep the first isosceles group on its own exact input/output contract."""

    profile = get_group_profile("27284")

    assert profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert profile.snapshot_theme_id == "15e9e844-7ed4-4bb6-8e57-79afb62e83d3"
    assert profile.source_group_id == "6fa6e46a-8e66-40ab-8b12-a830d8cec6fe"
    assert profile.workflow_kind == "content_rule"
    assert profile.content_rule_key == "isosceles-triangle-27284-base-from-sine"
    assert profile.strategy_key is None


def test_group_27285_uses_its_inverse_strict_isosceles_rule() -> None:
    """Separate the inverse side calculation from the preceding group rule."""

    profile = get_group_profile("27285")

    assert profile.source_group_id == "e815ef19-e5b1-4407-bcb3-011d096b8f46"
    assert profile.content_rule_key == "isosceles-triangle-27285-side-from-base-sine"
    assert profile.workflow_kind == "content_rule"


def test_profiles_select_strategies_from_explicit_data() -> None:
    """Catch missing groups or a return to dynamic module-path selection."""

    profiles = all_group_profiles()
    assert set(profiles) == set(EXPECTED_GROUPS)
    for group_key, (source_group_id, strategy_key, vertex_count) in EXPECTED_GROUPS.items():
        profile = get_group_profile(group_key)
        assert profile.source_group_id == source_group_id
        assert profile.strategy_key == strategy_key
        assert profile.expected_vertices == vertex_count
        assert not hasattr(profile, "module_path")


def test_profile_is_immutable_and_group_lookup_fails_before_runtime() -> None:
    """Catch mutable per-run globals and silent fallback to another group."""

    profile = get_group_profile("27547")
    assert profile.existing_solution_policy == "rewrite"
    assert profile.formula_symbols == "ab"
    with pytest.raises(FrozenInstanceError):
        profile.expected_vertices = 4  # type: ignore[misc]
    with pytest.raises(KeyError, match="unsupported group"):
        get_group_profile("99999")


def test_group_27238_selects_condition_rule_without_geometry_strategy() -> None:
    """Route the right-triangle group without pretending its SVG is grid geometry."""

    profile = get_group_profile("27238")

    assert profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert profile.snapshot_theme_id == "dd26db09-ca42-4fe4-b408-2f80383fd94a"
    assert profile.category_key == "1"
    assert profile.workflow_kind == "content_rule"
    assert profile.content_rule_key == "right-triangle-sine"
    assert profile.strategy_key is None


def test_group_27239_selects_the_same_right_triangle_content_rule() -> None:
    """Register the next sine-based right-triangle group explicitly."""

    profile = get_group_profile("27239")

    assert profile.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert profile.source_group_id == "d7569951-414e-4d7e-85d0-6f5509fc116f"
    assert profile.snapshot_theme_id == "dd26db09-ca42-4fe4-b408-2f80383fd94a"
    assert profile.category_key == "1"
    assert profile.group_order_index == 1
    assert profile.workflow_kind == "content_rule"
    assert profile.content_rule_key == "right-triangle-sine"
    assert profile.strategy_key is None


def test_group_27240_requires_cosine_and_hypotenuse() -> None:
    """Keep the cosine group strict about both its input and requested side."""

    profile = get_group_profile("27240")

    assert profile.source_group_id == "9333c06b-a69d-49be-81d0-297a0e6bc194"
    assert profile.group_order_index == 2
    assert profile.content_rule_key == "right-triangle-cosine-hypotenuse"
    assert profile.strategy_key is None


def test_group_27243_requires_tangent_ac_and_bc() -> None:
    """Register the strict tangent-to-opposite-cathetus content rule."""

    profile = get_group_profile("27243")

    assert profile.source_group_id == "f8e433ab-6dc0-41fc-9841-6de9135566c4"
    assert profile.content_rule_key == "right-triangle-tangent-opposite-cathetus"
    assert profile.strategy_key is None


def test_group_27242_requires_tangent_and_hypotenuse() -> None:
    """Route tangent tasks through their dedicated strict content rule."""

    profile = get_group_profile("27242")

    assert profile.source_group_id == "127bf3ef-3eff-47b2-b77c-87dc842421bb"
    assert profile.group_order_index == 3
    assert profile.content_rule_key == "right-triangle-tangent-hypotenuse"
    assert profile.strategy_key is None


def test_group_27244_uses_the_universal_right_triangle_rule() -> None:
    """Route every supported angle/function/side shape through one rule."""

    profile = get_group_profile("27244")

    assert profile.source_group_id == "fa52d73f-7f5b-44c8-a592-46efff4db916"
    assert profile.group_order_index == 5
    assert profile.content_rule_key == "right-triangle-universal"
    assert profile.strategy_key is None


@pytest.mark.parametrize(
    ("group_key", "source_group_id", "order_index"),
    [
        ("27247", "5a4134a0-4cbc-423d-896c-18154a429dce", 6),
        ("27249", "52ebad7f-0bd7-4663-8b9c-35331a27b143", 7),
        ("27250", "1b65c948-4216-4182-951d-4da316235480", 8),
    ],
)
def test_later_right_triangle_groups_use_the_universal_rule(
    group_key: str,
    source_group_id: str,
    order_index: int,
) -> None:
    """Keep later source groups on the shared role-normalized runner."""

    profile = get_group_profile(group_key)

    assert profile.source_group_id == source_group_id
    assert profile.group_order_index == order_index
    assert profile.content_rule_key == "right-triangle-universal"
    assert profile.strategy_key is None


@pytest.mark.parametrize(
    ("group_key", "source_group_id", "order_index"),
    [
        ("27265", "23402d00-846a-4db5-9103-a956e244203e", 9),
        ("27266", "e377cf2d-ded2-46d2-9c54-094d768f47a2", 10),
        ("27267", "a3245268-b5fc-4912-9066-f387cb9c5327", 11),
        ("27268", "85c32d94-6bcd-485d-8c81-000e8a8953be", 12),
        ("27269", "598b542c-547a-40b4-9b5c-7f1ebf063585", 13),
        ("27270", "fccb7e66-6f5f-425d-b013-20a28bc18dad", 14),
        ("27271", "07b024c7-a4a9-42da-8f06-3b76c754d39a", 15),
        ("27272", "db056adf-8ca1-490c-8a55-6e87b956a97e", 16),
        ("27273", "779b4486-f7f0-412d-9e71-20e2703a5c64", 17),
        ("27280", "068762af-3edb-4a5b-9b14-b3f8dbce0dec", 18),
        ("27336", "1c9d01cd-3ae5-4624-b97a-802f483b09d2", 19),
        ("27337", "80f2d73c-52e9-44cc-97db-4657d0c3cc74", 20),
        ("27338", "10c54900-a29d-471a-bd8c-9a42b59fb6e2", 21),
        ("27339", "369efb41-a0bc-4ac3-be7b-8b485c357f40", 22),
        ("27340", "d3c7e2f9-65e0-427f-b4d9-2d4874de0de3", 23),
        ("27341", "7760fde3-96e2-4f14-ba95-3fd58bbfe22e", 24),
        ("27342", "6404ea88-a14c-4e8c-a5df-60820dbd0a02", 25),
        ("27343", "0688995b-5e9c-4098-bc97-5fc541d5bdf2", 26),
        ("27344", "dfe23c14-0758-49bf-adbe-b0fe8578018b", 27),
        ("27357", "3a320928-1a84-4c55-ae7a-69ce25882da6", 28),
        ("27358", "b0095bf0-f6ce-4742-afd4-e8e172e452c6", 29),
        ("27431", "4b93b53e-bd57-4033-8213-a6201f5151bc", 30),
        ("27432", "da3ae05d-953c-4f39-b85a-7e4466ef499c", 31),
    ],
)
def test_altitude_groups_use_the_fail_closed_universal_rule(
    group_key: str,
    source_group_id: str,
    order_index: int,
) -> None:
    """Register every actual altitude group in current source order."""

    profile = get_group_profile(group_key)

    assert profile.source_group_id == source_group_id
    assert profile.group_order_index == order_index
    assert profile.content_rule_key == "right-triangle-altitude-universal"
    assert profile.strategy_key is None


@pytest.mark.parametrize(
    ("group_key", "source_group_id", "order_index", "content_rule_key"),
    [
        (
            "27617",
            "96477e5e-4194-4211-95ba-683876577f4f",
            32,
            "right-triangle-leg-hypotenuse-area",
        ),
        (
            "27618",
            "3d399961-7f2c-4c8f-a97d-69ec6df8d19b",
            33,
            "right-triangle-area-leg-difference",
        ),
        (
            "27742",
            "6bb5c896-1064-4510-bd34-9b625ae544fa",
            34,
            "right-triangle-acute-angle-difference",
        ),
        (
            "27753",
            "1cb9af83-8463-44ba-a407-de890b23e646",
            35,
            "right-triangle-acute-angle-ratio",
        ),
    ],
)
def test_later_elementary_right_triangle_groups_select_exact_content_rules(
    group_key: str,
    source_group_id: str,
    order_index: int,
    content_rule_key: str,
) -> None:
    """Route each elementary condition family through its own strict rule."""

    profile = get_group_profile(group_key)

    assert profile.source_group_id == source_group_id
    assert profile.group_order_index == order_index
    assert profile.content_rule_key == content_rule_key
    assert profile.strategy_key is None


@pytest.mark.parametrize(
    ("group_key", "source_group_id", "order_index", "content_rule_key"),
    [
        ("27761", "da62a5ad-58f1-482e-b597-fa9b3ce0d9de", 36, "right-triangle-median-angle"),
        ("27765", "07ff93c8-7436-49d5-9970-c471131e5e69", 37, "right-triangle-bisector-intersection-angle"),
        ("27770", "8cda3670-eb2b-47f6-aee2-87a18fc33a15", 39, "right-triangle-altitude-bisector-angle"),
        ("27771", "3ad3751b-dbcd-409f-85bc-bba308a09fde", 40, "right-triangle-altitude-bisector-inverse"),
        ("27772", "98f0e947-9327-4d19-b09b-a91dc805114e", 41, "right-triangle-altitude-line-angle"),
        ("27773", "34a912a3-be54-40ee-82c5-b1f595afba5a", 42, "right-triangle-altitude-median-inverse"),
        ("27774", "c519d5ac-8460-4fe4-82dd-39a6f89236c6", 43, "right-triangle-bisector-median-angle"),
        ("27775", "228ba65b-e3bb-42f4-a79c-e38be708cc6d", 44, "right-triangle-bisector-median-inverse"),
        ("27789", "be74920f-7317-46b2-90f7-91f4b05b43b2", 45, "right-triangle-altitude-length"),
        ("27790", "d1a1906b-4407-4824-ae72-78bb95e7ecd9", 46, "right-triangle-hypotenuse-projection-ah"),
        ("27791", "e731573a-c95b-4cc4-bfd6-dab7432d0a1c", 47, "right-triangle-hypotenuse-projection-bh"),
    ],
)
def test_later_angle_and_altitude_groups_select_strict_content_rules(
    group_key: str,
    source_group_id: str,
    order_index: int,
    content_rule_key: str,
) -> None:
    """Catch a missing registration or accidental fallback to a broad solver."""

    profile = get_group_profile(group_key)

    assert profile.source_group_id == source_group_id
    assert profile.group_order_index == order_index
    assert profile.content_rule_key == content_rule_key
    assert profile.strategy_key is None


def test_profile_registry_is_read_only() -> None:
    """Catch runtime mutation of the global group-to-strategy registry."""

    profiles = all_group_profiles()
    with pytest.raises(TypeError):
        profiles["99999"] = get_group_profile("27543")  # type: ignore[index]


def test_group_244982_rewrites_every_existing_solution() -> None:
    """Catch accidental preservation of old Pythagorean solutions in this group."""

    profile = get_group_profile("244982")

    assert profile.theme_title == "Треугольник"
    assert profile.theme_order_index == 3
    assert profile.group_order_index == 7
    assert profile.existing_solution_policy == "rewrite"


def test_group_244983_uses_the_rhombus_bounding_profile() -> None:
    """Catch a return to trapezoid-only parallel-pair validation for rhombi."""

    profile = get_group_profile("244983")

    assert profile.theme_title == "Ромб"
    assert profile.theme_order_index == 4
    assert profile.group_order_index == 0
    assert profile.existing_solution_policy == "rewrite"


def test_group_27553_selects_two_verified_rhombus_solutions() -> None:
    """Keep the arbitrary-quadrilateral group on its audited rhombus variant."""

    profile = get_group_profile("27553")

    assert profile.theme_title == "Произвольный четырехугольник"
    assert profile.theme_order_index == 5
    assert profile.group_order_index == 0
    assert profile.solution_text_profile == "rhombus-two-methods"
    assert profile.existing_solution_policy == "rewrite"


def test_remaining_arbitrary_quadrilateral_groups_use_rectangle_and_pick() -> None:
    """Enable both child-facing methods and rewrite stale source solutions."""

    for group_key in set(EXPECTED_GROUPS) - {"27553"}:
        profile = get_group_profile(group_key)
        if profile.theme_title != "Произвольный четырехугольник":
            continue
        assert profile.solution_text_profile == "quadrilateral-pick"
        assert profile.existing_solution_policy == "rewrite"


def test_oge_area_groups_select_their_exact_catalog_and_solution_behavior() -> None:
    """Catch routing these OGE groups through the old EGE snapshot or theme."""

    earlier_quadrilateral = get_group_profile("323750")
    quadrilateral = get_group_profile("323790")
    cells = get_group_profile("341675")
    triangle = get_group_profile("348403")

    for profile in (earlier_quadrilateral, quadrilateral, cells, triangle):
        assert profile.catalog_snapshot_id == "fd733f80-43d2-4b4a-b903-2423796cbee5"
        assert profile.category_key == "18"
        assert profile.snapshot_theme_id == "58adee76-92b1-4e53-9ad2-e89d0129d238"
        assert profile.theme_title == "Площади"
        assert profile.existing_solution_policy == "preserve"

    assert earlier_quadrilateral.group_order_index == 1
    assert earlier_quadrilateral.solution_text_profile == "quadrilateral-pick-first"
    assert quadrilateral.group_order_index == 2
    assert quadrilateral.solution_text_profile == "quadrilateral-pick-first"
    assert cells.group_order_index == 3
    assert triangle.group_order_index == 4


def test_group_245008_rewrites_only_missing_or_pipeline_annulus_solutions() -> None:
    """Keep references untouched while allowing deterministic annulus reruns."""

    profile = get_group_profile("245008")

    assert profile.category_key == "12"
    assert profile.theme_title == "Окружность"
    assert profile.theme_order_index == 3
    assert profile.group_order_index == 6
    assert profile.geometry_kind == "ring"
    assert profile.solution_scope == "missing_or_pipeline_generated"
    assert profile.existing_solution_policy == "rewrite"


def test_known_area_ring_groups_detect_task_geometry_and_given_side_at_runtime() -> None:
    """Keep task-varying ring facts out of immutable group profiles."""

    for group_key, order_index in (("315122", 7), ("315123", 8), ("315124", 9)):
        profile = get_group_profile(group_key)
        assert profile.category_key == "12"
        assert profile.theme_title == "Окружность"
        assert profile.group_order_index == order_index
        assert profile.geometry_kind == "ring"
        assert profile.solution_scope == "missing_only"
        assert profile.existing_solution_policy == "preserve"
        assert not hasattr(profile, "known_circle_area")
        assert not hasattr(profile, "ring_alignment")


def test_group_348499_selects_only_missing_three_method_solutions() -> None:
    """Keep reference solutions untouched and require all three area methods."""

    profile = get_group_profile("348499")

    assert profile.catalog_snapshot_id == "fd733f80-43d2-4b4a-b903-2423796cbee5"
    assert profile.category_key == "18"
    assert profile.snapshot_theme_id == "58adee76-92b1-4e53-9ad2-e89d0129d238"
    assert profile.theme_title == "Площади"
    assert profile.group_order_index == 5
    assert profile.solution_scope == "missing_only"
    assert profile.existing_solution_policy == "preserve"
