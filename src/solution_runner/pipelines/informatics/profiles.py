"""Audited single-code extra-byte groups from the informatics catalog."""

from solution_runner.pipelines.core.profile_definitions import _profile


_GROUPS = (
    ('9364', '88cfe7e0-7597-46ad-b077-de5bf6b4d812', 1),
    ('10289', '508a697a-b091-4a76-97b4-76f77e07f210', 4),
    ('10387', 'd095681a-b9df-4279-a0b2-9660a33ff351', 5),
    ('10476', '62cb143b-82ef-4aca-9f19-24fa8d67c125', 6),
    ('10503', 'd3756e4f-76bb-42cb-bf61-95119c4d3cb2', 7),
    ('11269', '8034bd2a-6c62-43a4-b2e8-992072da00d5', 8),
    ('11309', '605ab61f-39c2-438a-b018-7601cb02acae', 9),
    ('11349', '8e99ffaa-8756-41f1-a370-2af2eebc4120', 10),
    ('13409', '164359c3-a99d-412d-bf19-ce11855beadd', 12),
    ('13462', 'e6f6710a-31be-4be8-aa18-2d5bdb05da51', 13),
    ('15108', '6bc28cfb-38b2-4944-bcb5-e4e77f87bdbb', 16),
    ('15853', '80950a19-51f5-4f24-a99c-02f6ce8f4dad', 19),
    ('15981', 'deddffc9-5470-42c7-b83a-5901fdd08170', 21),
    ('23911', '899a6254-4f3d-46cc-bac0-4e6d3177171c', 30),
    ('26956', 'a568fd39-87a0-4c68-a902-eae153929e20', 31),
    ('27542', 'e3b7d301-e493-4198-b595-fbd2bf37b9fa', 34),
    ('29198', '87d99634-8c4b-4ef3-adbc-15f30ece7c50', 37),
    ('35985', 'b1a48333-2aa4-4618-a563-ac0a00c6ffd6', 41),
    ('38945', '337ffe32-336e-44d3-991e-0380b09b18df', 43),
    ('59835', 'e3a877f9-523f-44d0-8012-6042c86a5003', 51),
)

_TOTAL_GROUPS = (
    ('8101', 'a2b015bc-8d33-49c6-a7c2-82e94d0227c7', 0),
    ('5081', '3751d374-d915-4d52-b544-3446f0191ba9', 2),
    ('13359', 'd2399e88-bf58-47af-9c94-1ed193691e24', 11),
    ('13740', '0efbdbf5-14aa-4034-83a0-3525155eca3b', 14),
    ('14228', 'a8222658-1bae-4f11-bca4-59c263c6de43', 15),
    ('15629', '32b26433-4271-4b6d-ad27-b47c3ba00b33', 17),
    ('18082', 'd2982563-e375-4daf-984a-9e072eefa81c', 24),
    ('18715', '8c2c08e3-f645-4218-8c03-b1534c97900e', 27),
    ('19062', 'd4d1df05-7d82-4bee-9e55-3f2df66ad3d2', 29),
    ('35469', 'e63dff50-073f-4eba-b347-6902f3ab9b9c', 40),
    ('37146', '90ee6d0c-1fad-4a98-8225-fa580dbe2f74', 42),
    ('51980', '0f93716e-f6a2-4c1c-bef2-65d316fbfad3', 47),
    ('56511', 'e7f57618-4236-4a4c-8885-d5fe7973ce17', 49),
)


_PASS_GROUPS = (
    ('15798', '93055e31-9c7f-48fd-a431-6046623d4c00', 18),
    ('15923', 'ab0167a7-b2d1-48a6-b67f-a5d2a941f5f5', 20),
    ('16388', '93e03460-3460-4cc5-b3bc-472e503395a1', 22),
    ('17331', 'f9842472-c95c-4859-9868-7af07565744f', 23),
    ('18819', '929a3528-2a18-49d2-97d2-6e6eeb4350a4', 28),
    ('28688', 'c86aa8e0-cc01-4eb2-a62f-d077be81d20f', 36),
)


_TWO_DEPARTMENTS_GROUPS = (
    ('18494', '02a5c27e-5976-46be-ad01-863378aa81c6', 25),
    ('18561', '89fa70bc-a714-4437-b3ba-e5e20a42bacf', 26),
)


PROFILES = tuple(
    _profile(
        key, source_group_id, order,
        catalog_snapshot_id="4b8ce070-551c-4697-9b42-11c2617966d8",
        category_key="11",
        theme_title="Пароли с дополнительными сведениями",
        theme_order_index=0,
        snapshot_theme_id="d33e913c-5954-41fa-ae91-fd9e11ae3114",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="informatics-password-total-bytes",
        rewrite_existing_solution=True,
    )
    for key, source_group_id, order in _TOTAL_GROUPS
) + tuple(
    _profile(
        key, source_group_id, order,
        catalog_snapshot_id="4b8ce070-551c-4697-9b42-11c2617966d8",
        category_key="11",
        theme_title="Пароли с дополнительными сведениями",
        theme_order_index=0,
        snapshot_theme_id="d33e913c-5954-41fa-ae91-fd9e11ae3114",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="informatics-password-extra-bytes",
        rewrite_existing_solution=True,
    )
    for key, source_group_id, order in _GROUPS
) + tuple(
    _profile(
        key, source_group_id, order,
        catalog_snapshot_id="4b8ce070-551c-4697-9b42-11c2617966d8",
        category_key="11",
        theme_title="Пароли с дополнительными сведениями",
        theme_order_index=0,
        snapshot_theme_id="d33e913c-5954-41fa-ae91-fd9e11ae3114",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="informatics-pass-department-extra-bytes",
        rewrite_existing_solution=True,
    )
    for key, source_group_id, order in _PASS_GROUPS
) + tuple(
    _profile(
        key, source_group_id, order,
        catalog_snapshot_id="4b8ce070-551c-4697-9b42-11c2617966d8",
        category_key="11",
        theme_title="Пароли с дополнительными сведениями",
        theme_order_index=0,
        snapshot_theme_id="d33e913c-5954-41fa-ae91-fd9e11ae3114",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="informatics-pass-two-departments-extra-bytes",
        rewrite_existing_solution=True,
    )
    for key, source_group_id, order in _TWO_DEPARTMENTS_GROUPS
)
