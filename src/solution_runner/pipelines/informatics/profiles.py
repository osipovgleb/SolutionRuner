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
        content_rule_key="informatics-password-extra-bytes",
        rewrite_existing_solution=True,
    )
    for key, source_group_id, order in _GROUPS
)
