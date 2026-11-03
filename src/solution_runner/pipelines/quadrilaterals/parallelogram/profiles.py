"""Parallelogram groups bound to their reviewed parent methods."""

from solution_runner.pipelines.core.profile_definitions import _profile

from .midpoint_model import HEIGHT, PERIMETER, TWO_TRAPEZOID, TWO_TRIANGLE, VARIGNON

PROFILES = tuple(
    _profile(
        key,
        identifier,
        index,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="1",
        theme_title="Параллелограммы",
        theme_order_index=3,
        snapshot_theme_id="b83f22cf-01ea-4a6e-802d-0a2a1831924e",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for key, identifier, index, rule in (
        (
            "27806",
            "a777678a-338f-4d37-83da-fb5761b960b7",
            14,
            "parallelogram-angle-sum",
        ),
        (
            "27807",
            "8a177d33-717b-4f84-a898-b841ede1416b",
            15,
            "parallelogram-angle-difference",
        ),
        (
            "27808",
            "2f4bd1e4-0f0c-40a2-8ee2-5b55c6ec50f8",
            16,
            "parallelogram-diagonal-split-angle",
        ),
        (
            "27809",
            "b1cdc10e-d198-4f26-928a-dd0b51e7d0af",
            17,
            "parallelogram-perimeter-side-difference",
        ),
        (
            "27822",
            "db659783-b855-4b5e-93e9-1888832d4c31",
            20,
            "parallelogram-angle-ratio",
        ),
        (
            "27824",
            "474c396b-7d8f-47c3-ac20-c40e85568813",
            22,
            "parallelogram-perimeter-side-ratio",
        ),
        (
            "27817",
            "1343b073-2144-402b-a340-cdca2045ae4a",
            19,
            "rhombus-side-sixty-height",
        ),
        (
            "27828",
            "f0989282-8175-40f1-aa1a-7ce312b66ddd",
            25,
            "rhombus-side-sixty-long-diagonal",
        ),
        (
            "27829",
            "624a3e18-4dcc-4a89-88d1-d917ad67404a",
            26,
            "rhombus-diagonal-ratio-perimeter-height",
        ),
        (
            "27436",
            "e989a6f9-18f6-45e9-a084-2d5e9294e132",
            0,
            "parallelogram-sine-greater-height",
        ),
        (
            "27611",
            "213db071-d7cb-4b31-9c01-adefaa299371",
            8,
            "parallelogram-base-height-transfer",
        ),
        (
            "27612",
            "1cacd2f6-bd07-45c7-b945-ea61a66b1419",
            9,
            "parallelogram-area-greater-height",
        ),
        (
            "27613",
            "67ea3c5c-0452-4b50-b5a8-4a58460c1544",
            10,
            "rhombus-height-thirty-area",
        ),
        ("27614", "402797f0-041d-4bb3-8ec5-c925dc2cf1aa", 11, "rhombus-diagonals-area"),
        (
            "27615",
            "9fd6095f-9221-475f-8ae8-01b7f84e4cf0",
            12,
            "rhombus-area-known-diagonal",
        ),
        (
            "27616",
            "5f2f0435-f250-427f-b48a-800671449d79",
            13,
            "rhombus-area-diagonal-factor-small",
        ),
        ("27582", "99f7646a-3ef6-4ef7-8a55-da75d65a624e", 1, "square-diagonal-area"),
        (
            "27601",
            "0e0c7608-9d21-4d7f-b861-fd97b8966e76",
            2,
            "rectangle-area-difference-larger-side",
        ),
        (
            "27603",
            "86832ac9-ad4f-4595-be65-102713dc8103",
            3,
            "rectangle-area-ratio-perimeter",
        ),
        (
            "27604",
            "1f736624-c5c0-4a0b-8390-1d9f1e5a97f6",
            4,
            "rectangle-perimeter-area-larger-side",
        ),
        (
            "27605",
            "b12321a6-0a95-4445-8096-b3742783d932",
            5,
            "rectangle-perimeter-diagonal-area",
        ),
        (
            "27606",
            "6f8a0661-036c-433c-8cf6-cd5c949903ad",
            6,
            "rectangle-perimeter-area-diagonal",
        ),
        ("27845", "0638b40d-6f64-4dfc-8398-d598e5334386", 27, PERIMETER),
        ("317338", "07a0cb21-4434-46af-b91b-112adf950a2a", 30, TWO_TRAPEZOID),
        ("319056", "acad8e12-9935-4d79-9a1f-3aface7f792a", 31, VARIGNON),
        ("319057", "10245d06-828f-44a3-a575-e92fef7a32fc", 32, TWO_TRIANGLE),
        ("665285", "f43579ce-3c4e-4b2e-97a0-cab36f034bef", 34, HEIGHT),
    )
)
