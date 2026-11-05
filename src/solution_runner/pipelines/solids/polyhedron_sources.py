"""Reviewed volume methods, source SHA pins and actual highlighted vertex sets."""

from . import source_assets

PARENTS = {
    "solid-polyhedron-central-tetrahedron": (
        "db2954d3-3f3c-483c-973b-700456fa212c",
        (),
        "69b49d5b8e7db85154806fb617adb382ae584695dc7031f5951ad94b8d2a4fbc",
    ),
    "solid-polyhedron-half-box": (
        "d34118f2-df92-404c-9756-691d15191bcd",
        (("image_2", "055e71cf-4c71-4770-995d-eb83ef188e4f"),),
        "9571274c3822581362ff4638b594ccf8eea3c717c62703f16b79e36a6ecd75bd",
    ),
    "solid-polyhedron-pyramid-with-note": (
        "d34118f2-df92-404c-9756-691d15191bcd",
        (("image_2", "f1e8f90a-a3f6-47b5-9602-d515bccb558f"),),
        "63e0f8b5002ca0a392eba6ed219152a0072b89e06143a07b0503b474f60ffd0f",
    ),
    "solid-polyhedron-triangle-pyramid": (
        "184f9e75-5413-48f8-be41-ad8601b19de5",
        (("image_2", "b21b8664-9f31-4d8c-9a29-24cf9d53a88e"),),
        "1a7b2b0f575a01a9033bbadac570b6c812a0327ad741fd5bdf3245e1a3fa3509",
    ),
    "solid-polyhedron-face-pyramid": (
        "d6f29e5b-eab2-4eea-8703-8790f819b778",
        (),
        "588c7eb7d658edcad016b1cb8786897ac3265258689ebfb4340fbd2ad24f83f1",
    ),
}
STYLES = {
    "solid-polyhedron-central-tetrahedron": {
        "roles": (("condition", "solid", "db2954d3-3f3c-483c-973b-700456fa212c"),),
        "note": False,
        "preferred_axis": 2,
    },
    "solid-polyhedron-half-box": {
        "roles": (
            ("condition", "frame", "d34118f2-df92-404c-9756-691d15191bcd"),
            ("solution", "solid", "055e71cf-4c71-4770-995d-eb83ef188e4f"),
        ),
        "note": False,
        "preferred_axis": 2,
    },
    "solid-polyhedron-pyramid-with-note": {
        "roles": (
            ("condition", "frame", "d34118f2-df92-404c-9756-691d15191bcd"),
            ("solution", "solid", "f1e8f90a-a3f6-47b5-9602-d515bccb558f"),
        ),
        "note": True,
        "preferred_axis": 2,
    },
    "solid-polyhedron-triangle-pyramid": {
        "roles": (
            ("condition", "frame", "184f9e75-5413-48f8-be41-ad8601b19de5"),
            ("solution", "solid", "b21b8664-9f31-4d8c-9a29-24cf9d53a88e"),
        ),
        "note": False,
        "preferred_axis": 1,
    },
    "solid-polyhedron-face-pyramid": {
        "roles": (("condition", "solid", "d6f29e5b-eab2-4eea-8703-8790f819b778"),),
        "note": False,
        "preferred_axis": 2,
    },
}
SOURCES = {
    "db2954d3-3f3c-483c-973b-700456fa212c": (
        "db2954d3-3f3c-483c-973b-700456fa212c",
        "57ae139d06b6999abd7d20f16887794738cb660fdd7347b9c3a7109f2b7f154b",
    ),
    "d34118f2-df92-404c-9756-691d15191bcd": (
        "d34118f2-df92-404c-9756-691d15191bcd",
        "8a9f55218e948c387e93377a92166f60d7873b65c70b995606819fd62749e5d0",
    ),
    "055e71cf-4c71-4770-995d-eb83ef188e4f": (
        "055e71cf-4c71-4770-995d-eb83ef188e4f",
        "06bf0ee0d7693a42c0c9e439f243999f3db66c4bce5448d94c68f9f15afe4cb1",
    ),
    "f14f56b5-1995-40e7-af79-2730223ab14f": (
        "f14f56b5-1995-40e7-af79-2730223ab14f",
        "297c150c35d757cac57ee04620380facbabe3850ecc013d6a02c979736f6c1ed",
    ),
    "10b45bb8-3824-44fa-997f-4f2f0459b791": (
        "10b45bb8-3824-44fa-997f-4f2f0459b791",
        "c3cfe22046035bf461e03609c5d87d15f81becf78b008447a4f072660596e37d",
    ),
    "184f9e75-5413-48f8-be41-ad8601b19de5": (
        "184f9e75-5413-48f8-be41-ad8601b19de5",
        "9ba4f0b8d1cbcb7566b83d1cc4be573de4cc4a51ade9b5a6f0c15ef7907b2c09",
    ),
    "f1e8f90a-a3f6-47b5-9602-d515bccb558f": (
        "f1e8f90a-a3f6-47b5-9602-d515bccb558f",
        "c7e978992f3d8d9383e15ea904db45e522c259dc74f9cdf4a4a09c071a3d5cdd",
    ),
    "8ae29483-487b-4ed4-91c4-a8d2db9869bb": (
        "8ae29483-487b-4ed4-91c4-a8d2db9869bb",
        "56064f207b9d9917efa81d8244a8c766da519d2b7e5b6eadeeab7da11d32ed95",
    ),
    "fecdd5c1-4a21-4e24-9fd4-43e8df01eceb": (
        "fecdd5c1-4a21-4e24-9fd4-43e8df01eceb",
        "fc74c5db434d9cd01324d526d50bb009a53b898429b04e95fd668f2ceaf32939",
    ),
    "078ac6ef-17c7-418d-a2ef-aefb00cdab06": (
        "078ac6ef-17c7-418d-a2ef-aefb00cdab06",
        "2fecaf982463015a50e8bfe8b811bd37c537be00026635784d0f88e96c4ba074",
    ),
    "92c41e81-4da0-4789-a928-7b15438b4fc2": (
        "92c41e81-4da0-4789-a928-7b15438b4fc2",
        "ca8c9f478030dbcc07e3a0c4a1b46ebeef49fa21ae782bba320d732b641c6ef8",
    ),
    "a2589447-7b3e-412f-97fe-0b640284ad1f": (
        "a2589447-7b3e-412f-97fe-0b640284ad1f",
        "e53f5251f4c764a42824aa95618bae5086df93ee10acd286d85f525fbb86b35c",
    ),
    "b21b8664-9f31-4d8c-9a29-24cf9d53a88e": (
        "b21b8664-9f31-4d8c-9a29-24cf9d53a88e",
        "11d91e94c509f4a8bf03ab118c254a4dad61289e845332bf6412a2fe41f0a0bc",
    ),
    "f9d5a36e-5d1c-405d-8942-ae494c352c4e": (
        "f9d5a36e-5d1c-405d-8942-ae494c352c4e",
        "07f8d697a8e924685af8acd641cc3dccfa73eccfe37f1176da0a347900db49b4",
    ),
    "443ce805-6bc4-4a01-acc8-774c606afd49": (
        "443ce805-6bc4-4a01-acc8-774c606afd49",
        "d6184abe9c9469b403d0ec7291ad8104ba4313699a01190f31b9bafb4a2ecd43",
    ),
    "78f996f7-733f-409f-9a03-54f513bf35e3": (
        "78f996f7-733f-409f-9a03-54f513bf35e3",
        "45cf99356be6ca8647985840bbc5cd86853ef3aa6c7516769e4f24b4203920ef",
    ),
    "6d02c041-c7a4-4fee-8861-455a504b163f": (
        "6d02c041-c7a4-4fee-8861-455a504b163f",
        "bc9b7d0b2ffbde70a498b12c73624a451de804bd4a1f9274d87e06d8fba2d61f",
    ),
    "b41d2700-efe2-41e0-a0b8-71a97f105c8d": (
        "b41d2700-efe2-41e0-a0b8-71a97f105c8d",
        "4835d239c50f4021adf81e4525ad09e31fe33fe956cb709869b7b5664431170b",
    ),
    "d6f29e5b-eab2-4eea-8703-8790f819b778": (
        "d6f29e5b-eab2-4eea-8703-8790f819b778",
        "b707a859959457fa5cb6d684cbe6f1618651e8b0b13a1134594763304bb8a854",
    ),
    "8000164b-227e-4e7c-b8c2-892e4e40ef40": (
        "8000164b-227e-4e7c-b8c2-892e4e40ef40",
        "1343ede122c24a315c741dc1b4f01ccbff25741b0d2839a464a1feffa32f1b03",
    ),
    "f51ec298-b9e3-4479-9a2b-d802cafacedc": (
        "f51ec298-b9e3-4479-9a2b-d802cafacedc",
        "14fc5c12497310f97405e989698ea46e6c7157484ff610e218229426704860d9",
    ),
}
SOLIDS = {
    "db2954d3-3f3c-483c-973b-700456fa212c": ("A", "C", "B_1", "D_1"),
    "d34118f2-df92-404c-9756-691d15191bcd": None,
    "055e71cf-4c71-4770-995d-eb83ef188e4f": ("A", "B", "C", "D", "A_1", "B_1"),
    "f14f56b5-1995-40e7-af79-2730223ab14f": None,
    "10b45bb8-3824-44fa-997f-4f2f0459b791": ("A", "B", "C", "A_1", "B_1", "C_1"),
    "184f9e75-5413-48f8-be41-ad8601b19de5": None,
    "f1e8f90a-a3f6-47b5-9602-d515bccb558f": ("A", "B", "C", "B_1"),
    "8ae29483-487b-4ed4-91c4-a8d2db9869bb": ("B", "D", "B_1", "C_1"),
    "fecdd5c1-4a21-4e24-9fd4-43e8df01eceb": None,
    "078ac6ef-17c7-418d-a2ef-aefb00cdab06": ("A", "A_1", "B_1", "D_1"),
    "92c41e81-4da0-4789-a928-7b15438b4fc2": None,
    "a2589447-7b3e-412f-97fe-0b640284ad1f": ("A", "B", "C", "B_1"),
    "b21b8664-9f31-4d8c-9a29-24cf9d53a88e": ("A", "B", "B_1", "C_1"),
    "f9d5a36e-5d1c-405d-8942-ae494c352c4e": ("A", "B", "A_1", "D_1"),
    "443ce805-6bc4-4a01-acc8-774c606afd49": None,
    "78f996f7-733f-409f-9a03-54f513bf35e3": ("A", "D", "C_1", "D_1"),
    "6d02c041-c7a4-4fee-8861-455a504b163f": None,
    "b41d2700-efe2-41e0-a0b8-71a97f105c8d": ("A", "B", "B_1", "C_1"),
    "d6f29e5b-eab2-4eea-8703-8790f819b778": ("A", "B", "C", "D", "B_1"),
    "8000164b-227e-4e7c-b8c2-892e4e40ef40": ("A", "B", "C", "D", "C_1"),
    "f51ec298-b9e3-4479-9a2b-d802cafacedc": ("A", "B", "C", "D", "A_1"),
}


def source_bytes(source):
    return source_assets.source_bytes(source, SOURCES)


def review_parent(rule, primary, html, assets):
    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
