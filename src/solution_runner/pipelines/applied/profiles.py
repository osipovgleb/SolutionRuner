"""Applied groups from the profile mathematics catalogue."""

from ..core.profile_definitions import _profile

_GROUPS = (
    (
        "Рациональные уравнения и неравенства",
        2,
        "2b29bf78-2c25-43d5-a783-05d7a19fbb3e",
        "applied-algebraic-formula",
        (
            ("27973", "a748375e-f21e-4b2d-9f94-fd38b0fb68b2", 3),
            ("27978", "97f85ca0-8249-4680-a293-a368b5ab3090", 8),
            ("27988", "d54b7616-ab3c-4035-a5ab-97831577450f", 12),
            ("27989", "b2cf9988-5049-4f99-8e6a-510b63151bef", 13),
        ),
    ),
    (
        "Квадратные и степенные уравнения и неравенства",
        1,
        "e5298c3c-eb96-4171-9f42-a25162a40b17",
        "applied-polynomial-physical-model",
        (
            ("27955", "e1146327-705e-4b33-b47f-15c60f42d72e", 0),
            ("27957", "ba969dd0-abc1-4e0b-9823-661d4a77a287", 2),
            ("27959", "f37f608c-2d42-49d0-af23-ba5151d5d980", 4),
            ("27960", "7b2f7a14-4977-478e-a71a-744e10d82799", 5),
            ("27961", "b4d04d15-d0ba-499a-8c01-99d85274b0ec", 6),
            ("27962", "de18eb17-7714-4f82-a079-93b9b930e09c", 7),
            ("27963", "0b6d6f2a-f6d9-4f4f-a190-6db8137e7766", 8),
            ("27964", "653c53e4-8bb6-4867-a64f-832b5ee50708", 9),
            ("27965", "084f25b6-e540-4e1a-b6b6-2e3e57bc718d", 10),
            ("500252", "b34c8605-e066-45f6-916c-295fece3721f", 16),
            ("676852", "9d5a216a-282a-4829-b01c-e9f5019a2d08", 17),
        ),
    ),
    (
        "Линейные уравнения и неравенства",
        0,
        "e44915db-5f6d-4180-8265-3802b94ae135",
        "applied-algebraic-formula",
        (
            ("27953", "26d2c0c5-e5c8-431f-a136-de54942d5adb", 0),
            ("27954", "8f08c233-8bfb-4bdc-8be5-fca9c0f86c6b", 1),
        ),
    ),
    (
        "Квадратные и степенные уравнения и неравенства",
        1,
        "e5298c3c-eb96-4171-9f42-a25162a40b17",
        "applied-algebraic-formula",
        (
            ("27956", "32984504-6dd3-4aaa-92ae-6d5ca9d0a869", 1),
            ("27958", "fec6792f-8b0d-4bf3-a2f3-7e43120d9751", 3),
            ("27966", "8de202e3-c2ac-4138-b3b4-f2d5279a19d0", 11),
            ("27967", "c3e2ceff-d351-485f-89d0-c20c74bb1a25", 12),
            ("27968", "2c66c416-ab64-4022-8eae-ad736de4a35f", 13),
            ("27969", "fa46ca3e-d899-4849-81a4-678683a6df26", 14),
            ("500168", "5823ccab-aee3-4f25-84f0-24e1876c0617", 15),
        ),
    ),
)

PROFILES = tuple(
    _profile(
        key,
        source_id,
        order,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="10",
        theme_title=title,
        theme_order_index=theme_order,
        snapshot_theme_id=theme_id,
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for title, theme_order, theme_id, rule, groups in _GROUPS
    for key, source_id, order in groups
)
