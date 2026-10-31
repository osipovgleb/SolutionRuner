"""Audited EGE hyperbola groups; current condition images are preserved."""

from ..core.profile_definitions import _profile

PROFILES = tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="12",
        theme_title="Гиперболы",
        theme_order_index=2,
        snapshot_theme_id="4309cd49-7738-4b5a-b0d8-3892b940e5db",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="hyperbola-unshifted-value"
        if mode == "unshifted-value"
        else f"hyperbola-shift-{mode}",
        rewrite_existing_solution=True,
    )
    for key, group_id, index, mode in (
        ("508951", "84eff141-c86b-4919-bd7f-384a62eb21cf", 0, "value"),
        ("508961", "0c1b13d3-a625-4f9d-95f4-cef5cb087a19", 1, "argument"),
        ("508971", "b7df39c8-06a2-46ca-b69b-a7ad420cc81e", 2, "horizontal-value"),
        ("508983", "bec09ca3-a236-47aa-9fcd-776884b9a05a", 3, "horizontal-argument"),
        ("508993", "b4a0f3c7-c5de-4c56-a003-7c236d2be077", 4, "fractional-coefficient"),
        ("509001", "25605c37-1c45-4790-9713-6711d0b2090a", 5, "fractional-coefficient"),
        ("660801", "67db17c6-c0a4-477d-8564-a9eeb199d4f1", 6, "unshifted-value"),
    )
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="12",
        theme_title="Линейные функции",
        theme_order_index=0,
        snapshot_theme_id="90a5b726-e959-4600-a322-d9a21b6f257c",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="linear-function-graph",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("508895", "6839078b-a433-4316-9e90-27fec786e85c", 0),
        ("508903", "81973392-a7ad-4082-8629-023bfd52d154", 1),
        ("509197", "c19f96f0-7ab4-426b-89f4-4601f6751efa", 2),
        ("509213", "66299821-4c45-4d8e-a198-6a91ed1b388e", 3),
        ("509241", "c4645171-0814-48f2-8f17-0fa79015b877", 4),
    )
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="12",
        theme_title="Параболы",
        theme_order_index=1,
        snapshot_theme_id="ebd8f398-35d3-4cfc-97f7-7f09193f6760",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="quadratic-function-graph",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("508911", "810d546b-dad6-4287-8f51-fdf432d0ab1e", 0),
        ("508919", "17c47041-25ae-4756-9b0a-7711232b4757", 1),
        ("508927", "8a55a229-a2ce-4e32-970f-9adaa138f844", 2),
        ("508935", "269d57ec-f24d-4267-b8e2-767adf8e9f72", 3),
        ("508943", "ba381d9f-8361-4037-b296-48acc186c9a1", 4),
        ("509253", "8180e7f9-0d4e-4f69-bc1a-61b24c6200f1", 5),
        ("509262", "2a65e356-8f49-41e8-8795-5dcdc3056763", 6),
        ("564646", "7472b49f-b782-443f-8052-e0433cf8db74", 7),
    )
)
