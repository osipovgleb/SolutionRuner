"""Audited group bindings for classical probability."""

from solution_runner.pipelines.core.profile_definitions import _profile

PROFILES = tuple(
    _profile(
        key,
        source_id,
        order,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="4",
        theme_title="Классическое определение вероятности",
        theme_order_index=0,
        snapshot_theme_id="18297563-1a91-4066-8181-d335c4f155a5",
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for rule, members in (
        (
            "probability-counting-ratios",
            (
                ("320208", "aca65fc3-9dcc-48c1-9533-3454dce93395", 0),
                ("1001", "43894b00-c4a9-4f49-8b75-ab489f6c2128", 1),
                ("283579", "4e64dfd7-89c7-4b07-bbd2-f8687a76cdcc", 2),
                ("282857", "2a871227-b510-49ce-962a-f3e209a4cf4d", 3),
                ("282856", "7537fa3a-5e1a-4ede-ad85-fe415a90d373", 4),
                ("283639", "a1c6f1f9-6b03-4b4f-8ffa-e9618f6b4a45", 5),
                ("320186", "53bfc713-70ad-4fa9-aae8-012fc13601e1", 6),
                ("320189", "a6a5ac76-0634-488d-8996-1386f1197ba4", 7),
                ("320190", "fafb4633-b300-4191-889d-3833b2dd8571", 8),
                ("320191", "6988ddef-372e-4e9f-b4ab-6ecd575d9e46", 9),
                ("320192", "12d63040-3546-455d-9de3-57c43caec14b", 10),
                ("320193", "9785ff01-2e2a-48d4-b536-19525941f84b", 11),
                ("320194", "f5f4fe93-36b6-4a42-bd86-cc95add1de16", 12),
                ("325904", "1088ef37-0fc9-4221-9767-5dca400c362e", 15),
                ("500037", "8ec68f33-3726-453a-8c2a-d158be639f1d", 16),
                ("500250", "747ed88d-d0a7-475a-9569-8dcb90a6ac5c", 17),
                ("501210", "138bc80f-2378-4f90-a782-44162c7d79ea", 18),
                ("504230", "83e32ae5-4adc-436f-bf8a-77d5b89610cc", 19),
                ("1011", "31db1b10-b676-4fa8-9a90-172429b4538c", 23),
                ("1024", "f5c26d8b-091c-48b0-9518-76fef1e14244", 24),
                ("282855", "583cfcb8-6817-4920-bf65-310b6001d746", 26),
                ("282858", "3c9c7a2e-2eeb-4f88-ac43-f6da04779b68", 27),
                ("285922", "f2eb1bbb-d492-4e5d-aa91-a573055b0db2", 28),
                ("285923", "29e444f6-de58-47bd-8fc1-3f97e43e18fe", 29),
                ("285924", "38176cb7-3c6e-4f21-8920-8c647194cef6", 30),
                ("285925", "61e3e6ad-0c9b-4450-9198-ed7204a5d1a4", 31),
                ("285926", "0b2ef340-b93c-4bdd-81d2-cb64d5885c41", 32),
                ("285927", "92386a39-322e-432d-ade1-221f40865a46", 33),
                ("285928", "daa9741f-caac-4688-a77e-f28330d867a2", 34),
                ("320169", "e1727736-96a3-4b3d-aa84-7ef250b6ed3b", 35),
                ("320170", "4d40cde5-6690-489b-b4e2-4de37eacedb1", 36),
                ("320181", "77c2333b-e6b2-4946-ab71-70ab2760d390", 39),
                ("672740", "a53fab8e-ffb7-4815-b445-2d46c035a00c", 48),
                ("680564", "b1377d98-4517-491b-bfaa-09e34125acc2", 50),
                ("704175", "faa840b4-4dcd-4e67-9b5b-bdf70957aa5d", 52),
            ),
        ),
        (
            "probability-differences-and-frequency",
            (
                ("320195", "33a31890-5019-4cce-824a-3f8cc98127a5", 13),
                ("670263", "13214b50-dedb-4c03-95a0-517cc6bd29d1", 47),
                ("683036", "87e32be8-d7e0-4e32-9784-c170c0251370", 51),
            ),
        ),
        (
            "probability-uniform-integer-outcomes",
            (
                ("320209", "3b18936c-20ca-4484-a9cb-90694340e495", 14),
                ("509412", "a4e5b313-931c-407a-957f-8fa658935345", 20),
                ("320178", "e7959bb0-8c26-498b-85e1-b08685c17992", 37),
                ("320179", "cb768373-0f61-4461-9288-0e05916da825", 38),
                ("639942", "11e48e4a-66f1-475f-830b-0a3568eecfc4", 46),
            ),
        ),
        (
            "probability-fair-coins",
            (
                ("282854", "6130ae38-b164-45fd-ac58-fc125c7a41bb", 21),
                ("283467", "1bb57862-1a66-4ae5-9cd4-09c4b50f9929", 22),
                ("320183", "5326e1cc-21d0-4bdd-9966-ee2e540fc65b", 40),
                ("320185", "39539761-9f4e-40bd-821d-fec89256eb7d", 42),
            ),
        ),
        (
            "probability-fair-dice",
            (
                ("282853", "a1c64cd9-73dd-45e9-baea-4d6e91ce8a85", 25),
                ("320184", "b0998f99-f763-4e75-b3c4-4d31aa0b6ab3", 41),
                ("621760", "25e407e5-472d-4d9c-b51e-b5b1292f35ad", 44),
                ("639941", "c42ef718-96ef-45cd-9381-74e2c4a2077f", 45),
            ),
        ),
        (
            "probability-conditioned-dice-table",
            (
                ("508769", "993f76eb-c921-45d2-b77b-55d45bf046c5", 43),
                ("676847", "ea47fa50-45c5-40c3-8ebd-2d7ae7322cfa", 49),
            ),
        ),
    )
    for key, source_id, order in members
)

# Complex-event group bindings.
THEMES = (
    ("0e1c2dc6-575b-42dd-a945-6f90bd9dbf5d", "Теоремы о вероятностях событий", 0),
    ("1ccee1fe-99a1-4cea-8097-871032f7b66a", "Новые задания банка MathЕГЭ", 1),
)

GROUPS = (
    (
        "probability-two-source-mixtures",
        (
            ("320751", "c39a6ba1-07ad-4de3-b332-20f48c09e62b", 0, 0),
            ("320180", "3e388c31-a02c-4e52-9b35-7c5391a9fedc", 18, 0),
            ("319353", "ce3d445d-739e-4bc4-8c27-f2b3fb72d91a", 19, 0),
            ("320207", "360442d4-e629-42fd-a1f2-d646ae3c8444", 20, 0),
            ("320211", "a46aa7fd-390a-4dba-9c71-251c2155f91b", 21, 0),
            ("320177", "da31b464-6002-4ebc-865a-be27fb958cb6", 22, 0),
            ("320200", "52f3ffe9-c8f4-4d18-9772-c0472e01e3fe", 27, 0),
            ("508819", "8c4ce7a3-6b81-4fbd-a912-6a4bf64d01fa", 4, 1),
        ),
    ),
    (
        "probability-bernoulli-events",
        (
            ("509352", "753d2065-6f14-485c-9d39-dfc642c65d5d", 1, 0),
            ("320210", "dc181ceb-bd13-4566-bf06-f5ed5a525b48", 6, 0),
            ("320201", "c73edcd8-3f3d-4d59-8a28-978ba4142950", 7, 0),
            ("320173", "580332a8-27a0-40a8-b382-6a6a5b53329f", 11, 0),
            ("320175", "39b673d4-a737-4297-b676-608e61954653", 12, 0),
            ("320174", "d566ce1c-c0a1-4c3f-aefa-5be34bf68ef7", 17, 0),
            ("320205", "88cfd0ba-8436-4f48-afca-d74c86f671e4", 29, 0),
            ("501061", "278f589b-bb10-47d8-ac56-b03a057ae4ae", 31, 0),
            ("628364", "0455db23-aee8-4f0f-82a4-3f8a60334548", 43, 0),
            ("630095", "1ab37f5e-d721-4dc6-9dc6-adf4b8a0187a", 44, 0),
            ("635146", "7fee5e87-e9c7-4801-8b43-fe7df006b741", 45, 0),
            ("676848", "23e903ec-8529-4a56-88f8-df87be02128d", 48, 0),
            ("704176", "6ef3efd5-e612-4f24-a922-cda6cd604f56", 50, 0),
            ("508780", "72a6bb0c-d734-408a-9da3-f56da94fc13f", 0, 1),
            ("508808", "a0a60ebc-8fcb-48a8-b0ff-6c78338cbe24", 3, 1),
            ("508850", "76797b3c-dfc5-4e69-9fe3-36f923ff5e15", 7, 1),
        ),
    ),
    (
        "probability-independent-pairs",
        (
            ("319355", "f8725881-cc89-4a94-9375-a5da09bc0591", 2, 0),
            ("320202", "48fbe344-e13c-42e1-8001-b6ed867dded2", 28, 0),
            ("672742", "8e2e2b1d-e3df-4b00-84e0-2e0c68c86038", 46, 0),
        ),
    ),
    (
        "probability-event-sets",
        (
            ("320197", "230f18f0-98ec-404a-8ca1-91c9b1e8fd0b", 4, 0),
            ("320196", "afad2393-f630-4c4b-9d82-966d024bc22d", 5, 0),
            ("320176", "c7aa64e1-bb66-486f-9153-1be322ab39f3", 9, 0),
            ("509916", "152b3aaf-8312-4587-8fdf-95bd8e8680ee", 10, 0),
            ("320171", "419a8060-4e42-40b7-bf93-d7c4f3d9fc43", 14, 0),
            ("320203", "bf503710-22ca-4fe9-9c09-e354a577d98c", 25, 0),
            ("680565", "f1bbf5bc-b1c9-47eb-a5a6-7137ffc092d0", 49, 0),
            ("509313", "c48fafaf-8385-4a8d-add6-1426dbde1652", 11, 1),
        ),
    ),
    (
        "probability-joint-events",
        (
            ("510117", "6ba9807b-d8c7-4dfe-b685-525b037ff83d", 8, 0),
            ("320172", "a6caee2a-69c5-4088-bd08-37b55be77985", 23, 0),
            ("320452", "c7b52c1e-22c3-4d30-aa25-beba95873ba9", 32, 0),
        ),
    ),
    (
        "probability-retry-threshold",
        (
            ("320187", "8bc0d8d3-1e7b-40b3-ae47-42494725f42b", 13, 0),
            ("508830", "e9b6e971-0364-4db9-bd00-07ab7f0ef1ff", 5, 1),
        ),
    ),
    (
        "probability-finite-sequences",
        (
            ("320188", "1f6d4775-73e0-4e2d-87bf-13d1c40d7734", 15, 0),
            ("320206", "6d71b4b5-4795-4da4-b9eb-c6ec000f44e8", 16, 0),
            ("509078", "0c09ddc7-4585-49f1-8d59-07f5cafb1f53", 37, 0),
            ("508791", "e8e9e0e8-f070-47b3-b291-a817b2ca2163", 1, 1),
        ),
    ),
    (
        "probability-admission-tree",
        (("320199", "025102ba-214c-4e1e-8a33-9ef83cf50112", 24, 0),),
    ),
    (
        "probability-differences-and-frequency",
        (("320198", "fea29c41-a45a-45b7-bf38-08f91abfde2c", 26, 0),),
    ),
    (
        "probability-without-replacement",
        (
            ("500998", "322e1fd4-6ea1-4116-8ca5-8f8c33ed7916", 30, 0),
            ("621772", "bf8f9645-f2c5-4a55-9b7b-be42ec2a6e42", 42, 0),
            ("508840", "7c68ade9-e432-48b2-8e56-5867438dc7ad", 6, 1),
            ("663473", "f4ec0956-d7e0-488e-ae89-0eaaddc911a3", 12, 1),
            ("663475", "8ebf5570-1a18-448e-b51f-efb5cd5ef07d", 13, 1),
        ),
    ),
    (
        "probability-fair-dice",
        (
            ("508754", "5bbf0092-bdf4-4140-a8be-ae615251b3ab", 33, 0),
            ("508761", "97c43ae5-db26-4fa5-93c8-780f621cb833", 34, 0),
        ),
    ),
    (
        "probability-dice-stopping",
        (
            ("508792", "e931bc3e-2fcd-4582-98bd-ddea69ce76ab", 35, 0),
            ("674923", "f2c3c222-0d0d-4000-b576-842f027d20e0", 47, 0),
            ("509462", "396b6a28-86ad-4aa0-a1ff-8115fa55788a", 51, 0),
            ("508797", "113e99c2-1eaf-443d-a118-708172c2bd61", 2, 1),
        ),
    ),
    (
        "probability-custom-dice-bayes",
        (("508887", "b26697da-e023-4243-b5e5-9cd749bf4869", 36, 0),),
    ),
    (
        "probability-population-tree",
        (("509303", "e7499819-6d1c-42a4-90e1-57a972640300", 38, 0),),
    ),
    (
        "probability-conditional-diagrams",
        (
            ("509332", "8550c7de-4dc2-4f62-a39e-e42527139cfd", 39, 0),
            ("509342", "d1c5ae7b-08ce-4fd5-8811-e23fcedb6a26", 40, 0),
        ),
    ),
    (
        "probability-forward-walks",
        (("562239", "4fd5fc08-dc82-48f7-b15b-245ca0c30e42", 41, 0),),
    ),
    (
        "probability-record-tournament",
        (("508866", "5cc96058-d371-4ec2-a157-092654b7456b", 8, 1),),
    ),
    (
        "probability-knockout-tournament",
        (("508870", "44deeaa2-6c14-453b-87f3-8b744d73ef14", 9, 1),),
    ),
    (
        "probability-random-walk",
        (("508876", "828ec65a-9877-44fb-9028-79207b28232f", 10, 1),),
    ),
)

PROFILES += tuple(
    _profile(
        key,
        source_id,
        order,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="5",
        theme_title=THEMES[theme][1],
        theme_order_index=THEMES[theme][2],
        snapshot_theme_id=THEMES[theme][0],
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for rule, members in GROUPS
    for key, source_id, order, theme in members
)
