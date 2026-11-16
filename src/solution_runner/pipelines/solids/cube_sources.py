"""Pinned cube parent methods and byte-identical original diagram aliases."""

RULES = {
    "solid-cube-surface-from-volume": "surface_from_volume",
    "solid-cube-edge-from-surface-increase": "edge_from_surface_increase",
    "solid-cube-volume-factor": "volume_factor",
    "solid-cube-volume-from-diagonal": "volume_from_diagonal",
    "solid-cube-diagonal-from-volume": "diagonal_from_volume",
    "solid-cube-edge-from-volume-increase": "edge_from_volume_increase",
    "solid-cube-surface-factor": "surface_factor",
    "solid-cube-surface-from-diagonal": "surface_from_diagonal",
    "solid-cube-volume-from-surface": "volume_from_surface",
    "solid-cube-surface-factor-from-volume-factor": "surface_factor_from_volume_factor",
    "solid-cube-midpoint-section-angle": "midpoint_section_angle",
}

PARENTS = {
    "solid-cube-surface-from-volume": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        (),
        "577f11e442cac46233ef8ce0e1a1298413136e8425f9f421b1cd9c2b159025b5",
    ),
    "solid-cube-edge-from-surface-increase": (
        "d1baacd4-ff8f-4294-a14b-7ff9f6c241f0",
        (),
        ("bec703ac2ace0616a1dc00cc297b94e62a63c2872731356f30087f989e0b418d",
         "ca06263febd8ae4f7334e6085e617ce9abee215c4fdb29d2d0a6c4fc6f38601f"),
    ),
    "solid-cube-volume-factor": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        (),
        ("6eac6da39a3eaa21d9051ee492d940838fd52ddad0a3022c6619d6d8969e5619",
         "eefc671155fa7ea91f71c5bbf6ee51e4ba4ad4b982933f1a561551059fc805ee",
         "3d6d38e4aa56d854843b28629f179247b63c2afd92915e520f98b28efd251798",
         "56cf35aaa84572a5c1d2916efb357bcc1076bf36dc919ff8208d6494ce60eda8"),
    ),
    "solid-cube-volume-from-diagonal": (
        "bb12cfab-d13c-4da3-aab6-e13ed52880fe",
        (),
        ("689518687a51fa2ccb248af87ce2994f159893f3ca444dc191920948e0b2b86d",
         "5934b46871efd26aadb52941587aa9acc9f7caaf77cc257dfa1f9264a6d1f248",
         "c74c989871372d97f6c8356bf9144f0c9eceb1784b63c7488f2e90edb23d6089",
         "f2546d728c0df0d703a6eff07dd85b558a56733756e018e3afd5f8513289b054"),
    ),
    "solid-cube-diagonal-from-volume": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        (),
        ("8774c8af7557e7b95d06ea83417c1069d45c2ad205b88ca25c4d6ec907b47cc8",
         "29b5e04fb7cc4beafc09ba328173707185c182b153b6c31d7d630e879e6b46f2",
         "e5829b68ef2281e041e5922ca0a49777453359af1020519fbdedc266a93b7c13"),
    ),
    "solid-cube-edge-from-volume-increase": (
        "bd95f5ae-f6c7-4e43-9e4d-a0c495e33cc9",
        (),
        ("69a62813ed7635e1d9a39eb9644119b0f6fe458515da94a317cda72939433d64",
         "cd86462659a5419ef8038fa96b4728d5f2245abbefeb095276f74fcbbb2cca47",
         "4580e3ca100c40a82901c8526103334d330c16c81b5949724e277a4235c47151",
         "8d8847e4bb9424bc5ecbfd2aecd5a3041ddaffacef6b4062ca3fbd58fd28673f",
         "df18f24fddf3aca245865003d5761bd8176fe5ef0a97665e99deedc2e6811e43",
         "075cc0c06cded8b364140eafb8ee6498c570698ec1cd4c19cc5e5aec22f5eb3a",
         "292bff51a5468151dbebe4b0d1b5445df7d8458a7a0dd093df1d15d3f9e4caa1"),
    ),
    "solid-cube-surface-factor": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        (),
        ("dc579d7a008293e0f2d52db38d3369b793803e5cb09ea19d030e7d586da9ee0c",
         "223011ba124d3c8b05c17545ca7107bd549d2cb12aafb4cd9927a7dfa0f99376"),
    ),
    "solid-cube-surface-from-diagonal": (
        "a728e904-311c-492f-b00b-adeb4194ed2d",
        (),
        ("12a4c5a540ceef571c98ce4948c2eaba9f626b0035e5805878166af57f19293c",
         "62a1a421931567065ea8e233c2a6ea0c55e8106ce7c662ad4ca89d3d0c92c7de"),
    ),
    "solid-cube-volume-from-surface": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        (),
        ("7bc7d587b58321fb5df1f09e12061916f1d2ad1fb3f0af57f11bcb12fd158c16",
         "71e4b4f2205cf8d691b46f8c26ddad50caf9e76063f3f31bf7c4f86ac8364206",
         "aa097bb308cbf0874c0af0a639cbf345579ed6bdec88caa61a97a20792664b60",
         "ee69281943ce9a9790a3bddd571b8b3dc30a0fddabe754566046b070742fbd4c"),
    ),
    "solid-cube-surface-factor-from-volume-factor": (
        "ef1feec0-448e-4742-bf82-63b6e5851235",
        (),
        ("60d193a838a13dbd46e886418de8db5ee40ca8f9b2771763083e114817207310",
         "d060bad7610c54732ff440d97f92e7c81ae5288bc2071234aaadfe1ba940317e",
         "b2d2fea42c7c50916b9e616389624bf35b2785feefdcbaff75022b3924f5c740",
         "47e32d7f4b92f013b251167050f86b5d3f499192644baee576bb2358da34c5e1"),
    ),
    "solid-cube-midpoint-section-angle": (
        "a3eeb27f-7a83-4249-be6f-e1c84176b2df",
        (("image_1", "a3eeb27f-7a83-4249-be6f-e1c84176b2df"),),
        "c2b718a763e380f100db9bf3f62c4be3f6b701c1ff4908770ecd4b3bca95f6e4",
    ),
}

SOURCES = {
    "1a2dd07c-416a-40f6-b040-1a754d502b46": (
        "1a2dd07c-416a-40f6-b040-1a754d502b46",
        "510461a0380f2a3fb85e24da6ae4b49e0a0590d528cebc0118bc0953d9458cdf",
    ),
    "0ec9a0e8-1a01-4596-9456-4132439d64b3": (
        "d1baacd4-ff8f-4294-a14b-7ff9f6c241f0",
        "1358880a28575c21b07bfb9f1c793be06537e4ae1ffb14f4c4fd0de6025eed1c",
    ),
    "211136e1-2696-442b-b772-700b4c8a4311": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        "a949e956f9b8c7b048449b2c9c74f8cf95e5f902d1c2fc4ff33b60d5135e5e81",
    ),
    "39c99c62-cff3-4d3c-ba24-bed3972e44ea": (
        "39c99c62-cff3-4d3c-ba24-bed3972e44ea",
        "1d968ce7ce73e47b182291188a2a20b6bbe0dd1c06345d8cfdc4d8c7430e2c1e",
    ),
    "616eaf24-3197-47d7-bb8e-a5cca0379dd3": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        "a949e956f9b8c7b048449b2c9c74f8cf95e5f902d1c2fc4ff33b60d5135e5e81",
    ),
    "a3eeb27f-7a83-4249-be6f-e1c84176b2df": (
        "a3eeb27f-7a83-4249-be6f-e1c84176b2df",
        "76a54c1195e01db5b33f5aecf053aadf3d20e69f799a671a3b4e5ebe07a7bf6b",
    ),
    "baa176f5-7ac2-44e0-a3c6-5d6c3fcc0dc5": (
        "baa176f5-7ac2-44e0-a3c6-5d6c3fcc0dc5",
        "4bcd86d3007ab6611a1aa691dde257056305bff1615e82d18f2e1f0380fdbda2",
    ),
    "a728e904-311c-492f-b00b-adeb4194ed2d": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        "a949e956f9b8c7b048449b2c9c74f8cf95e5f902d1c2fc4ff33b60d5135e5e81",
    ),
    "b4aeeee7-f2bc-4c88-b7ba-32b0429b91df": (
        "b4aeeee7-f2bc-4c88-b7ba-32b0429b91df",
        "86adeb8b7ee3605dc7a27af73889e4dc29e91594c0c3245c77c1945f3b119030",
    ),
    "bb12cfab-d13c-4da3-aab6-e13ed52880fe": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        "a949e956f9b8c7b048449b2c9c74f8cf95e5f902d1c2fc4ff33b60d5135e5e81",
    ),
    "bd268e8a-fc8c-4b36-8c19-db6b6a1f825b": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        "a949e956f9b8c7b048449b2c9c74f8cf95e5f902d1c2fc4ff33b60d5135e5e81",
    ),
    "bd95f5ae-f6c7-4e43-9e4d-a0c495e33cc9": (
        "d1baacd4-ff8f-4294-a14b-7ff9f6c241f0",
        "1358880a28575c21b07bfb9f1c793be06537e4ae1ffb14f4c4fd0de6025eed1c",
    ),
    "ef4a5163-c4df-4442-8cbc-d04ccff29a05": (
        "1a2dd07c-416a-40f6-b040-1a754d502b46",
        "510461a0380f2a3fb85e24da6ae4b49e0a0590d528cebc0118bc0953d9458cdf",
    ),
    "d1baacd4-ff8f-4294-a14b-7ff9f6c241f0": (
        "d1baacd4-ff8f-4294-a14b-7ff9f6c241f0",
        "1358880a28575c21b07bfb9f1c793be06537e4ae1ffb14f4c4fd0de6025eed1c",
    ),
    "ef1feec0-448e-4742-bf82-63b6e5851235": (
        "ef1feec0-448e-4742-bf82-63b6e5851235",
        "a7538e512d967ff4fcde2c6ac421e8613c7f4c37a84b870ec24d9675a9aaba4b",
    ),
}

MODE_SOURCES = {
    "surface_from_volume": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        "616eaf24-3197-47d7-bb8e-a5cca0379dd3",
        "a728e904-311c-492f-b00b-adeb4194ed2d",
        "bb12cfab-d13c-4da3-aab6-e13ed52880fe",
        "bd268e8a-fc8c-4b36-8c19-db6b6a1f825b",
    ),
    "edge_from_surface_increase": (
        "0ec9a0e8-1a01-4596-9456-4132439d64b3",
        "39c99c62-cff3-4d3c-ba24-bed3972e44ea",
        "bd95f5ae-f6c7-4e43-9e4d-a0c495e33cc9",
        "d1baacd4-ff8f-4294-a14b-7ff9f6c241f0",
    ),
    "volume_factor": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        "616eaf24-3197-47d7-bb8e-a5cca0379dd3",
        "a728e904-311c-492f-b00b-adeb4194ed2d",
        "bb12cfab-d13c-4da3-aab6-e13ed52880fe",
        "bd268e8a-fc8c-4b36-8c19-db6b6a1f825b",
    ),
    "volume_from_diagonal": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        "616eaf24-3197-47d7-bb8e-a5cca0379dd3",
        "a728e904-311c-492f-b00b-adeb4194ed2d",
        "bb12cfab-d13c-4da3-aab6-e13ed52880fe",
        "bd268e8a-fc8c-4b36-8c19-db6b6a1f825b",
    ),
    "diagonal_from_volume": (
        "1a2dd07c-416a-40f6-b040-1a754d502b46",
        "211136e1-2696-442b-b772-700b4c8a4311",
        "616eaf24-3197-47d7-bb8e-a5cca0379dd3",
        "a728e904-311c-492f-b00b-adeb4194ed2d",
        "bb12cfab-d13c-4da3-aab6-e13ed52880fe",
        "bd268e8a-fc8c-4b36-8c19-db6b6a1f825b",
        "ef4a5163-c4df-4442-8cbc-d04ccff29a05",
    ),
    "edge_from_volume_increase": (
        "0ec9a0e8-1a01-4596-9456-4132439d64b3",
        "bd95f5ae-f6c7-4e43-9e4d-a0c495e33cc9",
        "d1baacd4-ff8f-4294-a14b-7ff9f6c241f0",
    ),
    "surface_factor": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        "616eaf24-3197-47d7-bb8e-a5cca0379dd3",
        "a728e904-311c-492f-b00b-adeb4194ed2d",
        "b4aeeee7-f2bc-4c88-b7ba-32b0429b91df",
        "bb12cfab-d13c-4da3-aab6-e13ed52880fe",
        "bd268e8a-fc8c-4b36-8c19-db6b6a1f825b",
    ),
    "surface_from_diagonal": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        "616eaf24-3197-47d7-bb8e-a5cca0379dd3",
        "a728e904-311c-492f-b00b-adeb4194ed2d",
        "bb12cfab-d13c-4da3-aab6-e13ed52880fe",
        "bd268e8a-fc8c-4b36-8c19-db6b6a1f825b",
    ),
    "volume_from_surface": (
        "211136e1-2696-442b-b772-700b4c8a4311",
        "616eaf24-3197-47d7-bb8e-a5cca0379dd3",
        "a728e904-311c-492f-b00b-adeb4194ed2d",
        "baa176f5-7ac2-44e0-a3c6-5d6c3fcc0dc5",
        "bb12cfab-d13c-4da3-aab6-e13ed52880fe",
        "bd268e8a-fc8c-4b36-8c19-db6b6a1f825b",
    ),
    "surface_factor_from_volume_factor": ("ef1feec0-448e-4742-bf82-63b6e5851235",),
    "midpoint_section_angle": ("a3eeb27f-7a83-4249-be6f-e1c84176b2df",),
}


def source_bytes(source):
    from . import source_assets

    return source_assets.source_bytes(source, SOURCES)


def review_parent(rule, primary, html, assets):
    from . import source_assets

    return source_assets.review_parent(
        rule, primary, html, assets, parents=PARENTS, sources=SOURCES
    )
