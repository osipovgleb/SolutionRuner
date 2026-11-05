"""Check exact reusable SVG/PNG identities, figure roles and image-free parents."""

import hashlib
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section
from sphere_source_cases import CASES, GROUPS, plan

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.sphere_sources import SOURCES, source_bytes

PICTURED = tuple(c for c in CASES if c["context"]["normalized_content"]["assets"])


@pytest.mark.parametrize("source", SOURCES)
def test_source_bytes_are_exact_and_png_is_not_disguised_as_svg(source):
    raw = source_bytes(source)
    assert hashlib.sha256(raw).hexdigest() == SOURCES[source][1]
    if source == "14103aaf-178e-4060-b49c-dadde8b6f6b5":
        assert raw.startswith(b"\x89PNG\r\n\x1a\n") and SOURCES[source][0].endswith(
            ".png"
        )
    else:
        assert b"<svg" in raw and b"<image" not in raw


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_reuse_exact_compatible_scenes_without_new_diagrams(case):
    handler = get_handler(GROUPS[case["group"]]["rule"])
    assert handler.diagram_specs(case["context"]) == ()
    ctx = deepcopy(case["context"])
    before = section(ctx, "condition")
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    if case["group"] == "27125":
        assert (
            ctx["normalized_content"]["assets"] == []
            and section(ctx, "condition") == before
        )
    else:
        assert section(ctx, "condition")["asset_keys"] == ["image_1"]
        assert len(ctx["normalized_content"]["assets"]) == 1
    assert not BeautifulSoup(section(ctx, "solution")["html"], "html.parser").find(
        "img"
    )
    if case["task"] == "76363":
        assert (
            'width="250"' in section(ctx, "condition")["html"]
            and ctx["normalized_content"]["assets"][0]["asset_id"]
            == "14103aaf-178e-4060-b49c-dadde8b6f6b5"
        )


@pytest.mark.parametrize("case", PICTURED, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "field", ["foreign", "url", "duplicate", "unreferenced", "wrong_object"]
)
def test_unreviewed_or_unreferenced_figure_metadata_fails_closed(case, field):
    ctx = deepcopy(case["context"])
    assets = ctx["normalized_content"]["assets"]
    a = assets[0]
    if field == "foreign":
        a["asset_id"] = "foreign"
    elif field == "url":
        a["url"] = "https://example.com/foreign.svg"
    elif field == "duplicate":
        assets.append(deepcopy(a))
    elif field == "unreferenced":
        s = section(ctx, "condition")
        soup = BeautifulSoup(s["html"], "html.parser")
        soup.img.decompose()
        s["html"] = str(soup)
        s["asset_keys"] = []
    else:
        other = (
            "ef77deff-825b-435b-a9f9-3a5f5cbc3a5d"
            if case["group"] not in {"27097", "27174"}
            else "d95b4646-f780-4918-a15e-d51589cb18c4"
        )
        soup = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
        soup.img["data-asset-id"] = other
        soup.img["src"] = "/assets/" + other
        section(ctx, "condition")["html"] = str(soup)
        a["asset_id"] = other
        a["url"] = "/assets/" + other
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("width", "0"),
        ("width", "-1"),
        ("width", "100%"),
        ("width", "99999"),
        ("onclick", "doSomething()"),
        ("style", "display:none"),
    ],
)
def test_presentational_width_has_bounded_syntax_and_other_attributes_remain_strict(
    attribute, value
):
    case = next(c for c in CASES if c["task"] == "76363")
    ctx = deepcopy(case["context"])
    s = section(ctx, "condition")
    soup = BeautifulSoup(s["html"], "html.parser")
    soup.img[attribute] = value
    s["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_png_cannot_move_into_solution_or_three_sphere_sum():
    case = next(c for c in CASES if c["task"] == "76363")
    ctx = deepcopy(case["context"])
    s = section(ctx, "condition")
    soup = BeautifulSoup(s["html"], "html.parser")
    image = str(soup.img)
    soup.img.decompose()
    s["html"] = str(soup)
    s["asset_keys"] = []
    ctx["normalized_content"]["sections"].append(
        {
            "key": "solution",
            "html": "<p>" + image + "</p>",
            "asset_keys": ["image_1"],
            "section_id": "solution:1",
            "transformation_target_id": "section:solution:1",
        }
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    ctx = deepcopy(case["context"])
    s = section(ctx, "condition")
    s["html"] = s["html"].replace(
        "Радиусы двух шаров равны 7 и 24. Найдите радиус шара, площадь поверхности которого равна сумме площадей поверхностей двух данных шаров.",
        "Радиусы трех шаров равны 1, 6 и 8. Найдите радиус шара, объем которого равен сумме их объемов.",
    )
    volume_case = next(c for c in CASES if c["task"] == "27125")
    with pytest.raises(ContentPlanError):
        plan(volume_case, ctx)
