"""Exam equation group bindings for the corresponding topic."""

from solution_runner.pipelines.core.profile_definitions import _profile

PROFILES = tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="14",
        theme_title="Показательные уравнения",
        theme_order_index=0,
        snapshot_theme_id="a55db974-0491-4d22-b9c0-b9da72748cb1",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-exponential-quadratic-interval",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("502094", "508b774c-5cc8-4fd3-8c8a-9643a32cfdc5", 0),
        ("516760", "a0f73691-5be8-43c8-b1d8-dcd5a0b16172", 1),
        ("528517", "35edc567-3c07-4426-910d-514aafbe8366", 6),
        ("552108", "88afa490-c812-4c3d-9783-95ffa9105617", 7),
    )
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="14",
        theme_title="Показательные уравнения",
        theme_order_index=0,
        snapshot_theme_id="a55db974-0491-4d22-b9c0-b9da72748cb1",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-exponential-quadratic-interval",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("514081", "11fd2bf5-9dc8-4bcf-b23d-058a43bda4df", 4),
        ("502999", "085d37a0-a36c-4151-b553-772b842f0737", 5),
        ("562757", "0246aad8-476b-4f08-abbc-df34cb6f4dc4", 10),
    )
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="14",
        theme_title="Показательные уравнения",
        theme_order_index=0,
        snapshot_theme_id="a55db974-0491-4d22-b9c0-b9da72748cb1",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-exponential-factor-interval",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("513605", "5ffc5f69-4510-4944-8d12-ec2606a2d5a7", 2),
        ("503127", "24d1d62a-527a-4cc3-87c6-f9141cafa00f", 3),
        ("555583", "19b41c28-547a-4bd3-aaa9-cee084e25ca6", 8),
        ("562032", "f8a7aa38-3466-4b8b-b8f3-3ea580ffd5e7", 9),
        ("640910", "9b1ab182-42a0-4418-a1ee-b4e5b05b567f", 11),
    )
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="14",
        theme_title="Рациональные уравнения",
        theme_order_index=1,
        snapshot_theme_id="e3d4e88d-f782-4715-9211-1d11895851ca",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-rational-interval",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("519423", "493526d5-2102-4af7-b871-7adfe73b0b84", 0),
        ("563297", "ae6448b4-02e6-4a2e-bfbc-3b3f161ae8e0", 1),
        ("627406", "2196854a-5d58-4a09-89d7-5409f71d10ee", 2),
    )
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="14",
        theme_title="Иррациональные уравнения",
        theme_order_index=2,
        snapshot_theme_id="44135092-4f14-4c2f-b6a4-ea493f74f47a",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for key, group_id, index, rule in (
        ("521850", "8e6c137b-3551-4b7d-81ef-3ae824d6f0d4", 0, "exam-radical-interval"),
        ("520994", "3f749430-7c46-4bb2-bbbd-b80b574198db", 1, "exam-radical-interval"),
        ("519658", "3fdc7d89-728d-437e-a9e4-ce21d4f7d1b3", 2, "exam-radical-interval"),
        (
            "507572",
            "bab6cffa-ae6c-4355-a8e6-80eb23292bfa",
            3,
            "exam-nested-radical-interval",
        ),
        ("549170", "0aba816a-019f-4f32-8b63-9d4c6ce66326", 4, "exam-radical-interval"),
        ("639112", "1cc36301-e0e1-4d40-a292-7a9a005dbd72", 5, "exam-radical-interval"),
    )
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="14",
        theme_title="Ло га риф ми че ские уравнения",
        theme_order_index=3,
        snapshot_theme_id="7824b997-6388-471c-8e7b-7d796c7a7bca",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-logarithmic-interval",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("514082", "0faa7354-dfa7-4c49-ad42-19b0c07fbe4b", 0),
        ("517739", "bb6ef5e4-bb8c-4f73-9016-2fa230f18d45", 1),
        ("514623", "61aeb52c-6b40-4b9a-a2a2-e416b195d7fd", 2),
        ("502053", "79666940-ac16-4d76-93b9-43eca05949a1", 3),
        ("525377", "3c8b455f-ae67-4e7c-83e3-e1335da29360", 4),
    )
)


PROFILES += tuple(
    _profile(
        key,
        group_id,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="14",
        theme_title="Ло га риф ми че ские уравнения",
        theme_order_index=3,
        snapshot_theme_id="7824b997-6388-471c-8e7b-7d796c7a7bca",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key="exam-logarithmic-branches",
        rewrite_existing_solution=True,
    )
    for key, group_id, index in (
        ("550261", "eae85fbe-8667-4f75-9439-88ed8d8a7ab4", 5),
        ("555265", "7ed66a0d-29a5-4964-9571-29eed85be85f", 6),
        ("561853", "735f4d49-cf5e-4d47-90b3-3b2c9764760d", 7),
        ("643200", "7c6a747c-1b97-4b1a-9d9b-3338a36f7828", 8),
        ("643677", "c5184bb1-3deb-4b48-8e01-2868659ff387", 9),
        ("693985", "914862fc-4438-4a08-9a73-ef800ae16921", 10),
    )
)
