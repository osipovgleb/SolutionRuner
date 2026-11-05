"""Pinned complete parent methods and audited original circle SVG aliases."""

import gzip
import hashlib
from importlib.resources import files

from ..core.errors import ContentPlanError
from .circumcircle_sources import PARENTS as CIRCUMCIRCLE_PARENTS
from .circumcircle_sources import SOURCES as CIRCUMCIRCLE_SOURCES
from .incircle_sources import PARENTS as INCIRCLE_PARENTS
from .incircle_sources import SOURCES as INCIRCLE_SOURCES

PARENTS = {
    "circle-inscribed-special-chord": (
        "aab6d4fd-29ab-4b85-9ce0-3bf072ab9106",
        (("image_2", "2791f260-5ce1-4c3c-87b7-9bdc63ecbf10"),),
        "ba96b5fe22f20d971239694e91095254ab9d39baee6f8abc2fa099ead55d0f5e",
    ),
    "circle-central-angle-difference": (
        "515f640e-4cd6-40ee-94b4-d171ac58f6ad",
        (("image_1", "515f640e-4cd6-40ee-94b4-d171ac58f6ad"),),
        "7e4c4a84dbc180a8dc867b566e837c8b37c67ca55ef5f0821bc39f421a9ba29d",
    ),
    "circle-inscribed-angle-difference": (
        "e37b7d86-ef1d-473b-8ef1-2777aefff55d",
        (),
        "4273da01981f4c6ba69a1224f2ca1ae519bbb4154188f232b8d3d57dc0bad0d2",
    ),
    "circle-inscribed-angle-arc-fraction": (
        "40ccd98b-48c9-469c-b30c-bbd010257d7c",
        (),
        "3bb5c1618d16a3bea8312f495f621d1fe7c3db1ad424a95a9d2f9284db229c74",
    ),
    "circle-inscribed-angle-two-arcs": (
        "d98c679b-1fdf-4382-9fad-5c11e6512d0f",
        (),
        "0491450e39d6ac38089942026fbd35156c2a07c3de2221b80f628f09d808564c",
    ),
    "circle-diameters-inscribed-to-central": (
        "1f80d796-67fd-4b3b-9edc-e038caf927ee",
        (),
        "fe6934735ffe1aa62bbbaa9721850f388480b504e80e5ce3678a4153a8bbcc6f",
    ),
    "circle-diameters-central-to-inscribed": (
        "1f80d796-67fd-4b3b-9edc-e038caf927ee",
        (),
        "45b78f9a3afe133eb860f433143761d597c879f443821363836670720cd5ae5d",
    ),
    "circle-secant-angle-arc-difference": (
        "f98a097b-c129-44ea-b49b-059bde4c8963",
        (),
        "fce3960501562b7a4234272edcab7925a8959230844f88c274919a9e0f92f9cc",
    ),
    "circle-chord-thirty-radius": (
        "03407436-f0c4-4cab-aaf7-d1ac07758183",
        (("image_2", "37a12d63-5fb7-446e-9cad-41be89cdaaa5"),),
        "468f8134bd0e08753140c7c943f23e3851d713c667c1c24ee1ed69852968b7af",
    ),
    "circle-chord-obtuse-radius": (
        "ba29ffaf-2266-4074-8d9a-b0af840fa294",
        (("image_2", "cebe4bd3-9c4c-47ff-962d-bdd8515f4933"),),
        "1915edc2a96d0833ecc92a9382a81b0c69bc85f0357b4b5b41e4498d33df6a99",
    ),
    "circle-chord-arc-ratio-inscribed": (
        "fa9b1335-5d14-421c-ad1f-f75492af3f92",
        (),
        "6e21f5d83ef7fcdc5f5c0c4bc51474b2516c487bf56163898d3a0370168bd941",
    ),
    "circle-tangent-chord-angle-from-arc": (
        "1fdab1cc-720e-4514-b05d-d9163cbf99dd",
        (),
        "864bb61a22bac21307e0bcb8f8db19b07b1ca9e527016b215a8bd98d854315c4",
    ),
    "circle-central-angle-from-tangent-base": (
        "d6035e07-cca6-4352-80a7-e671530a4363",
        (("image_2", "22cfa237-3e19-4574-8062-5929258e12ab"),),
        "f314c443cb9938f32cef1d8e37a97ae674c9725e92ea9f07e24e975d5cce3448",
    ),
    "circle-two-tangents-angle-from-arc": (
        "d6035e07-cca6-4352-80a7-e671530a4363",
        (),
        "5172b979509dfef76d289090ae2842d5f5ab387a691e50217a4a067e81394abb",
    ),
    "circle-two-tangents-arc-from-angle": (
        "d6035e07-cca6-4352-80a7-e671530a4363",
        (),
        "6e48292af05fe7fac59b1a60373322542b1162bacae402761b5a1d8ab81a512e",
    ),
    "circle-tangent-centre-near-angle": (
        "04c45fcc-f49e-434f-b8fe-b3254ed2719a",
        (),
        "61897e21feda6d81af7653add3cdebc65e3e433fba84337a6eaf6a7005dc21b3",
    ),
    "circle-tangent-centre-near-arc": (
        "04c45fcc-f49e-434f-b8fe-b3254ed2719a",
        (),
        "41d22faf2678b9bf3abed7fb793cb4b2ed8e860e30f2214e1a070a479ce3fe47",
    ),
    "circle-tangent-centre-far-angle": (
        "9d345fef-61ad-4320-ae6c-980925039824",
        (),
        "26875bad19ea330a8cf61cf04d7bce232ff8b76bb59c0b56a5aebfd1909dc2c7",
    ),
    "circle-tangent-centre-far-arc": (
        "9d345fef-61ad-4320-ae6c-980925039824",
        (),
        "fbfa499cd253b0b08f8a8638ffcdc00aeccc014bb884d41e2717b074ce8f6c20",
    ),
    "circle-three-arc-ratio-largest-angle": (
        "93bf921d-8eb2-48ae-ac48-10b377c66641",
        (),
        "f2936739ac6df073e2590ba5990c78726bc2b652db6857b00dd4cc7eafba654f",
    ),
    "circle-cyclic-opposite-angle": (
        "b2848d10-0706-4113-b70b-fee6abd8eb06",
        (),
        "641e7d0817c922be3ccb7cc04ff584daa08aaada445475bc6b1472cace4c3543",
    ),
    "circle-cyclic-four-arcs-angle": (
        "b2848d10-0706-4113-b70b-fee6abd8eb06",
        (),
        "c96ef012bdb5228797769127a9d59d3cec891cf37d1c3763dc7feb81b4b7642a",
    ),
    "circle-cyclic-four-arc-ratio": (
        "b2848d10-0706-4113-b70b-fee6abd8eb06",
        (),
        "77f6310053cbbc8d8e5611bd4c61cae897e558d031c69f1450c674bef61752f0",
    ),
    "circle-cyclic-angle-sum": (
        "81716d48-eee4-4e17-884b-3ef8bedd9276",
        (),
        "340f9aab370c063ff8fbe3c446f87b84e5e283da3cd34999c3530550745eec91",
    ),
    "circle-cyclic-angle-difference": (
        "5cbeeb21-d482-4558-8370-cf2fa3dea811",
        (),
        "c27c7bcd5bca3a58645127b1d44895b06733a98e0841f255b073d93a6da3f53a",
    ),
    "circle-cyclic-unnamed-largest-angle": (
        "a581e5c7-5ae0-4d79-83a1-c70ea8452116",
        (),
        "0797706965a1113a62d382819204e25a1eec96fc19a4ab1554f4ab339ff84dce",
    ),
}

SOURCES = {
    "2791f260-5ce1-4c3c-87b7-9bdc63ecbf10": (
        "2791f260-5ce1-4c3c-87b7-9bdc63ecbf10",
        "a2be915328f5492b78e47e67719e80261dca1abdd23b04b0393f0db38a2a06f8",
    ),
    "aab6d4fd-29ab-4b85-9ce0-3bf072ab9106": (
        "aab6d4fd-29ab-4b85-9ce0-3bf072ab9106",
        "f6e9ff0e699966e7aeab1b8d38787a35fa84f330e2f7c303ae8934423b9188b4",
    ),
    "1f80d796-67fd-4b3b-9edc-e038caf927ee": (
        "1f80d796-67fd-4b3b-9edc-e038caf927ee",
        "d7de5d0df467f351ddd562bee5dc6b24727db426f42f8ea40b783936f3be5e61",
    ),
    "3a014817-745a-4049-8437-07d8337f8f20": (
        "3a014817-745a-4049-8437-07d8337f8f20",
        "c35ec6c4c6f2e1c741bec47524bf6edc6a2aca49668ca02665bb2f7e91790729",
    ),
    "40ccd98b-48c9-469c-b30c-bbd010257d7c": (
        "40ccd98b-48c9-469c-b30c-bbd010257d7c",
        "1e1e1273e8640d69bee3355ffa5a4bf3a2ea37bd830d4f8f3514cf3c38f3cd21",
    ),
    "45075378-fe37-4226-87bf-d90d9275317e": (
        "45075378-fe37-4226-87bf-d90d9275317e",
        "da09a494eac19901edf1f663a6c3fdb4e63493114b2aaf290ebafb3b91cc85f8",
    ),
    "515f640e-4cd6-40ee-94b4-d171ac58f6ad": (
        "515f640e-4cd6-40ee-94b4-d171ac58f6ad",
        "8bc55c1fb21e9deb925a5a21bb849fe2df6515d24dd92177c115dd9c0ee0dbcd",
    ),
    "5be3c78f-0682-4cce-a623-1e7ff255692c": (
        "1f80d796-67fd-4b3b-9edc-e038caf927ee",
        "d7de5d0df467f351ddd562bee5dc6b24727db426f42f8ea40b783936f3be5e61",
    ),
    "8aee4b45-3b33-4f1b-b6c3-236cf0eeb1f1": (
        "8aee4b45-3b33-4f1b-b6c3-236cf0eeb1f1",
        "1070993890807a48c6085ed0b945078d7450656d209bd4f66521bd91a90bfedc",
    ),
    "d98c679b-1fdf-4382-9fad-5c11e6512d0f": (
        "d98c679b-1fdf-4382-9fad-5c11e6512d0f",
        "a794f19bcdff114f3817368cfbda8626d938cef8a96cd8e4386ca811ddaf13d2",
    ),
    "e37b7d86-ef1d-473b-8ef1-2777aefff55d": (
        "e37b7d86-ef1d-473b-8ef1-2777aefff55d",
        "7fc9937004a20f86de08bf32fed05f078eda44425bf42c855c99a36dbb7283ab",
    ),
    "e5fc5324-bed5-42ef-a335-d244924dfe9a": (
        "e5fc5324-bed5-42ef-a335-d244924dfe9a",
        "f6703ed7641df92842f2eadc63bd4fd1cfa423d4cce4dd16f8f336427a3d0969",
    ),
    "f98a097b-c129-44ea-b49b-059bde4c8963": (
        "f98a097b-c129-44ea-b49b-059bde4c8963",
        "927bfbd86a3240c54661c4d598584ce8fddc71d01ccf574a059f6fcdd67f50c9",
    ),
    "03407436-f0c4-4cab-aaf7-d1ac07758183": (
        "03407436-f0c4-4cab-aaf7-d1ac07758183",
        "7d6443f56f9ce839d2865a9a5f925ea29b13003488b9a0b8235f99b047f95b75",
    ),
    "04c45fcc-f49e-434f-b8fe-b3254ed2719a": (
        "04c45fcc-f49e-434f-b8fe-b3254ed2719a",
        "aef29386f0b4c2f3df2049231f175cad12079ec1f8bb3dd9488cf8e2e8942569",
    ),
    "1fdab1cc-720e-4514-b05d-d9163cbf99dd": (
        "1fdab1cc-720e-4514-b05d-d9163cbf99dd",
        "5652c3dc23b08863928dc2d583eef383768536c2d71f6500c7b10323f22ae7d7",
    ),
    "9d345fef-61ad-4320-ae6c-980925039824": (
        "9d345fef-61ad-4320-ae6c-980925039824",
        "89d9f56fbe2e8a916e2fffb98c87ad27568688e79e8cb823a4a22eb258f26037",
    ),
    "37a12d63-5fb7-446e-9cad-41be89cdaaa5": (
        "37a12d63-5fb7-446e-9cad-41be89cdaaa5",
        "34a5d22adb153645860ffaa0f4aa0316e18885badcafb8c404750c002b92c5ef",
    ),
    "22cfa237-3e19-4574-8062-5929258e12ab": (
        "22cfa237-3e19-4574-8062-5929258e12ab",
        "18f8f62300b4e1dc7cefd746a05f2c8e3105275658c74bc4f87725ef8dc1b09e",
    ),
    "ce2fa07b-34f1-44dc-833f-deb1f5d7af2d": (
        "ce2fa07b-34f1-44dc-833f-deb1f5d7af2d",
        "a21395192df0f9ece0699ede82b13a3a0fa2075e49ebd39fd2c6a9687e62a861",
    ),
    "ba29ffaf-2266-4074-8d9a-b0af840fa294": (
        "ba29ffaf-2266-4074-8d9a-b0af840fa294",
        "578236f8174db7ca8e32053498e7da85a31880b328907661ba5e99e6bbeeaac1",
    ),
    "cebe4bd3-9c4c-47ff-962d-bdd8515f4933": (
        "cebe4bd3-9c4c-47ff-962d-bdd8515f4933",
        "066ffc4775e4a74173cf2e96e476d36c70e5246877ab0410f6202011a285e8c3",
    ),
    "d6035e07-cca6-4352-80a7-e671530a4363": (
        "d6035e07-cca6-4352-80a7-e671530a4363",
        "88c62c1a2a5c8f6004edfe4983d6b442cf88f3aecd2df80f64de9c9e7fbfa7a2",
    ),
    "fa9b1335-5d14-421c-ad1f-f75492af3f92": (
        "fa9b1335-5d14-421c-ad1f-f75492af3f92",
        "695d8753a9320b6b99a2f5ba0b0c5bedf8c33cb44459fb788fb80a874bac01b7",
    ),
    "93bf921d-8eb2-48ae-ac48-10b377c66641": (
        "93bf921d-8eb2-48ae-ac48-10b377c66641",
        "68b52d35936f2b4e134d5fa11d3c8122ffb28ff1457099c5b7b51409caec2709",
    ),
    "02f4ca89-190b-489e-8a40-02295b1a6991": (
        "02f4ca89-190b-489e-8a40-02295b1a6991",
        "2dfb79636b86b482eb23fcd850a47a4dfa5cc4ca1da07bace46e4668ec1492b4",
    ),
    "efe00e1f-ac2e-450b-aa7d-166764145c7b": (
        "efe00e1f-ac2e-450b-aa7d-166764145c7b",
        "dfbe7e81387756db50a7a3f399423c6ab89cde9158fb57cbd56b0397ab2e4bc3",
    ),
    "b2848d10-0706-4113-b70b-fee6abd8eb06": (
        "b2848d10-0706-4113-b70b-fee6abd8eb06",
        "e3737dc4fd4613e554517b118df3e98d007753d9a4f601c39bdde65153f0a6ec",
    ),
    "81716d48-eee4-4e17-884b-3ef8bedd9276": (
        "81716d48-eee4-4e17-884b-3ef8bedd9276",
        "df807b2e52b236540d4e6643e318141a0be94caa4972e61ddec98f6de1181b60",
    ),
    "fe7c367d-af9e-4cfd-8626-cf65c3c64ac2": (
        "fe7c367d-af9e-4cfd-8626-cf65c3c64ac2",
        "0248c082fbf7c2759b9db9692e044e45d7649c7cf8b7b40ebe436d739106ca83",
    ),
    "5cbeeb21-d482-4558-8370-cf2fa3dea811": (
        "5cbeeb21-d482-4558-8370-cf2fa3dea811",
        "65f3383abab5d41791c0120c59baa73ab2e828a82e0169e489fd3de366c78892",
    ),
    "a581e5c7-5ae0-4d79-83a1-c70ea8452116": (
        "a581e5c7-5ae0-4d79-83a1-c70ea8452116",
        "18bd3666e90cbb219afa7d325fd8957e85b69bb6d910d76bc17cf8a8b72a922d",
    ),
    "fd4a0e7f-e14a-49f6-a218-c19216826aed": (
        "fd4a0e7f-e14a-49f6-a218-c19216826aed",
        "ef4e17252e4d76335bce927dd6a7cdf1bbb09ae16bc955a41314784b49153219",
    ),
}


PARENTS = PARENTS | INCIRCLE_PARENTS | CIRCUMCIRCLE_PARENTS
SOURCES = SOURCES | INCIRCLE_SOURCES | CIRCUMCIRCLE_SOURCES


def source_bytes(source):
    if source not in SOURCES:
        raise ContentPlanError("the circle-angle source needs a review")
    canonical, digest = SOURCES[source]
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + canonical + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ContentPlanError("the reviewed circle-angle SVG changed")
    return raw


def review_parent(rule, primary, html, assets):
    if rule not in PARENTS:
        raise ContentPlanError("an explicit reviewed circle-angle rule is required")
    expected, figures, digest = PARENTS[rule]
    if (
        primary != expected
        or not isinstance(html, str)
        or hashlib.sha256(html.encode()).hexdigest() != digest
    ):
        raise ContentPlanError("the complete reviewed circle-angle parent changed")
    if not isinstance(assets, (tuple, list)) or any(
        not isinstance(a, dict) for a in assets
    ):
        raise ContentPlanError(
            "complete circle-angle parent asset metadata is required"
        )
    if [(a.get("asset_key"), a.get("source_asset_id")) for a in assets] != list(
        figures
    ) or any(a.get("url") != "/assets/" + a["source_asset_id"] for a in assets):
        raise ContentPlanError("the reviewed circle-angle solution figures changed")
    for source in (primary, *(s for _, s in figures)):
        source_bytes(source)
