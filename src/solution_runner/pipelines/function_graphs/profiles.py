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


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="12",
        theme_title="Корни",
        theme_order_index=3,
        snapshot_theme_id="2c174e5c-7ad9-45b7-a156-ecd473a586d9",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="square-root-function-graph",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("509113", "623e833c-987f-4646-86ac-87d29d5f20f7", 0),
        ("509118", "a91d1c0d-4a76-46a1-a3e3-258f3979ef59", 1),
    )
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="12",
        theme_title="Показательные и логарифмические функции",
        theme_order_index=4,
        snapshot_theme_id="723e5f49-44e9-42c7-a8ca-fb36e5f1b020",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exponential-logarithmic-function-graph",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("509009", "324926c8-52c0-465b-8641-d3f51fa885b2", 0),
        ("509026", "00acdb28-fb44-4d31-ac72-568b56e142d3", 1),
        ("509042", "98eaf7b1-86a0-4cad-a8f7-a101d7677b27", 2),
        ("509060", "90d6c8e1-bcaf-495a-8ca8-f983c0ee83b0", 3),
        ("509089", "094fd911-e396-4404-81a8-149ec7570468", 4),
        ("509095", "208e5358-dd99-4be7-8923-c22009ebc956", 5),
        ("509101", "eb24ec93-513e-4eb7-803c-4fdd262cebfd", 6),
        ("509107", "b6671477-8b0e-45cd-a1ee-d9631ab46b73", 7),
        ("639480", "6da4137a-9f0c-40d0-9e4f-56b9e5568975", 8),
        ("639672", "c9e9525f-56ff-4af2-abd0-50aebdce894b", 9),
        ("660992", "a7fef2f7-2b5e-4ec3-99dc-468ab6f2b058", 10),
    )
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="12",
        theme_title="Тригонометрические функции",
        theme_order_index=5,
        snapshot_theme_id="02cd0ffc-cae6-440e-a7ac-f871005481cd",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="trigonometric-function-graph",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("509123", "3f9a9b12-ae6e-4a41-a4e3-33b0ddde6d7e", 0),
        ("509130", "78d1644e-e731-41e3-a520-09c74f7778aa", 1),
        ("509137", "e33fe014-4f84-487c-b1e2-3bf1ff61d8f7", 2),
        ("509143", "2afd4f31-6828-4bf4-89d0-d5c87d75c334", 3),
        ("509287", "62dfad83-e285-49c6-8d35-45529737fbfb", 4),
        ("509295", "b5af23a7-522c-44d5-8059-f0ee821154ec", 5),
        ("676854", "4bbcf71d-b730-4734-9bec-7fdd759f9de6", 6),
        ("676931", "38e1398b-00ef-48c6-b4c4-e5fac35b598c", 7),
    )
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="12",
        theme_title="Комбинированные задачи",
        theme_order_index=6,
        snapshot_theme_id="57b3ab9c-eb47-4a5e-bdbc-76a596696889",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="mixed-function-intersection",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("509149", "2d498fc2-d247-4e01-9e92-f088a0775254", 0),
        ("509158", "c3467e04-91dd-4112-b6ba-e1ab319c57bd", 1),
        ("509167", "06a0383d-5d90-4326-87fa-0b5213314992", 2),
        ("509182", "482f829e-9575-4765-a074-5e233662cfe1", 3),
        ("509271", "ebc21c36-881f-482c-b229-fe4c05024aad", 4),
        ("509280", "75565e3e-b067-45e6-91e6-03eca55f5bc8", 5),
        ("642371", "33cee078-0454-4a5c-8755-cc35762a865b", 6),
        ("642407", "43b9d96e-a857-4612-bcd0-5f6fe0ca281c", 7),
        ("661823", "ed94ec9f-7c71-413c-a9fb-de4b9484361e", 8),
    )
)
