"""Fixed catalog scope and protocol constants for polygon assets."""

DEFAULT_MCP_URL = "https://lessons-helper.ru/mcp"

DEFAULT_CATALOG_SNAPSHOT_ID = "4073fc7b-2056-4697-b18b-38741c94d0f4"

DEFAULT_SOURCE_SITE_ID = "7bed2492-5b8b-4c88-9be8-7d47916cd7c6"

DEFAULT_CATEGORY_KEY = "9"

DEFAULT_CATEGORY_TITLE = "9. Задачи на квадратной решетке"

DEFAULT_THEME_TITLES = (
    "Трапеция",
    "Треугольник",
    "Ромб",
    "Произвольный четырехугольник",
)

EXPECTED_VERTICES_BY_THEME = {
    "Трапеция": 4,
    "Треугольник": 3,
    "Ромб": 4,
    "Произвольный четырехугольник": 4,
}

FIXED_THEME_CONFIG = {
    "Трапеция": {
        "snapshot_theme_id": "26af5056-7c19-4148-85a2-ce95069d8760",
        "source_theme_id": "284",
        "order_index": 2,
        "source_groups_count": 7,
    },
    "Треугольник": {
        "snapshot_theme_id": "3913765c-3750-456e-aaff-2fc050bc8821",
        "source_theme_id": "286",
        "order_index": 3,
        "source_groups_count": 8,
    },
    "Ромб": {
        "snapshot_theme_id": "785f5813-b3f0-41cd-b6a1-6c63c4223d5e",
        "source_theme_id": "285",
        "order_index": 4,
        "source_groups_count": 1,
    },
    "Произвольный четырехугольник": {
        "snapshot_theme_id": "3bfd66e9-836c-4eda-a293-9885053ec4bd",
        "source_theme_id": "122",
        "order_index": 5,
        "source_groups_count": 23,
    },
}

FIXED_SOURCE_GROUPS = {
    "Трапеция": (
        ("fc5fc7a7-75ba-41d4-9bb7-4fee7b1b8be1", "27556"),
        ("ae4b8e1f-4ff2-4085-aee5-d3be39ccdbd6", "27557"),
        ("416046da-eecc-4473-83fd-b1b6c799a7e6", "27558"),
        ("0719750c-08ff-450c-bc16-3a65989caf9a", "27559"),
        ("3fb2e89d-9858-4c76-9683-d2d348ce4a35", "27560"),
        ("f2422780-bacb-4231-a06a-b89e855fc801", "244985"),
        ("0be1e4bb-4e88-43d0-8f03-2d4b1440773c", "244986"),
    ),
    "Треугольник": (
        ("4808d0b7-aa63-4a5f-85ed-da28c8f80b18", "27543"),
        ("b8fcbdc6-7967-4bc0-99b1-3fa49d5d824f", "27544"),
        ("0d938f6c-b012-4013-8dad-778add652e11", "27545"),
        ("d371408f-f616-4ed0-9cea-85f27fc30c4e", "27546"),
        ("96309f98-73c1-4abc-8005-73a4307e7295", "27547"),
        ("7e1ba8c1-23dc-4e04-aec2-67e23ef52cc7", "27548"),
        ("3e818284-d58c-43a6-b7b4-c21a48e5a425", "27549"),
        ("a3e9590e-400a-4e2e-9fcc-a4ddc94e53ab", "244982"),
    ),
    "Ромб": (("c7fb645b-bb12-48f9-86c9-de6bd980389e", "244983"),),
    "Произвольный четырехугольник": (
        ("0efa9c9d-8b0a-4eda-8f91-3bab53034f85", "27553"),
        ("8692d319-27c2-4e8b-994a-6efa20a7adac", "27554"),
        ("e779214c-ef69-400f-9516-db1e3cec409d", "27555"),
        ("65378636-e6f5-4087-8d36-37bf60e01556", "244987"),
        ("21f4102f-5758-4069-8ade-e35d3c1a91e4", "244988"),
        ("07db163e-8cb4-4fb9-abda-11ea84c72697", "244989"),
        ("c1720bed-72fd-4c28-8cc8-ab67cbab3449", "244990"),
        ("500815ad-983f-4658-820c-e63a4c3ca08e", "244991"),
        ("dfbc0d00-a0ee-4e3e-8791-369cf64339cc", "244992"),
        ("482c8645-573c-4d09-962a-10f9347e346a", "244993"),
        ("4af236f2-0dc6-44d1-b99e-d604fbe803b3", "244994"),
        ("1de2d522-204a-439e-99c1-37eb45881192", "244995"),
        ("07793db5-7983-4a49-81fc-2a1c04a21599", "244996"),
        ("c311c7ee-6156-4164-b052-dee139e6feb4", "244997"),
        ("a56949ab-bcc3-409d-8375-a216927ed92a", "244998"),
        ("a6c625ec-3b46-48ff-a1d5-a4518995a144", "244999"),
        ("d4f8b1b5-4a4f-4cca-9523-fcd32ac1e8f0", "245000"),
        ("8fa38806-4fb0-45d2-98e8-da85dc47ff1b", "245001"),
        ("07702ba0-2f65-4693-a842-cf44c1a0b194", "245002"),
        ("d0d1abe1-9b69-479d-8f43-b6f9182e861f", "245003"),
        ("5934b527-a4dc-49aa-95c5-4e748661b4f2", "245004"),
        ("186ffd8e-c830-476e-8361-98e8ba5dadf8", "245006"),
        ("2d78a6aa-7d44-4509-ac8e-534dc0a59349", "245007"),
    ),
}

REQUIRED_MCP_TOOLS = {
    "get_asset",
    "get_asset_file",
    "get_problem_asset_target_context",
    "get_problem_pipeline_state",
    "get_problem_transformation_context",
    "get_source_asset",
    "get_source_catalog_children",
    "get_source_catalog_section_images",
    "delete_problem_transformation",
    "prepare_source_asset_upload",
    "replace_problem_asset",
}

REQUIRED_ROLLBACK_MCP_TOOLS = {"delete_problem_transformation"}

PNG_CONTENT_TYPE = "image/png"

BMP_CONTENT_TYPES = frozenset({"image/bmp", "image/x-ms-bmp"})

RASTER_CONTENT_TYPES = frozenset({PNG_CONTENT_TYPE, *BMP_CONTENT_TYPES})

SVG_CONTENT_TYPE = "image/svg+xml"

MCP_PROTOCOL_VERSION = "2025-06-18"

CONVERTER_PROFILE = "grid-polygon-svg-v1"
