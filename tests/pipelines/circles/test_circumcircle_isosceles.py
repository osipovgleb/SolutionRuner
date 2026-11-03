"""Four methods, reviewed repeated references and the circumcenter boundary."""

import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from circumcircle_source_cases import CASES, generated, plan, read
from midpoint_source_cases import replay, section, solution_html
from test_circumcircle_lifecycle import apply_offline, prepared
from test_circumcircle_methods import verify
from test_iso_trapezoid_figures import check_labels
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.circles.circumcircle_isosceles_content import (
    validation_context,
)
from solution_runner.pipelines.circles.circumcircle_isosceles_model import (
    CONDITION_KEY,
    DETAIL,
    DETAIL_KEY,
    kind,
)
from solution_runner.pipelines.circles.circumcircle_isosceles_svg import figure_svg
from solution_runner.pipelines.circles.circumcircle_model import read_question
from solution_runner.pipelines.circles.quantity_sources import source_bytes
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.triangles.right.construction_svg import _bounds, _tag

ISOSCELES = [c for c in CASES if c["group"] == "27923"]
PARENT = next(c for c in ISOSCELES if c["task"] == "27923")
OBTUSE_CASES = [c for c in ISOSCELES if kind(read(c["context"])) == "obtuse"]


def condition(a, b):
    return f"<p>Боковые стороны равнобедренного треугольника равны {a}, основание равно {b}. Найдите радиус описанной окружности этого треугольника.</p>"


def right_context():
    ctx = deepcopy(PARENT["context"])
    sec = section(ctx, "condition")
    image = str(BeautifulSoup(sec["html"], "html.parser").find("img"))
    sec["html"] = image + condition(5, r'<span data-inline-latex="5\sqrt{2}"></span>')
    return ctx


def test_parent_has_three_references_and_the_unique_validation_view_keeps_input_intact():
    ctx = deepcopy(PARENT["context"])
    before = deepcopy(ctx)
    assert (
        len(
            BeautifulSoup(section(ctx, "solution")["html"], "html.parser").find_all(
                "img"
            )
        )
        == 3
    )
    clean = validation_context(ctx, read_question)
    assert ctx == before and clean != ctx
    assert (
        len(
            BeautifulSoup(section(clean, "solution")["html"], "html.parser").find_all(
                "img"
            )
        )
        == 1
    )
    assert section(clean, "solution")["asset_keys"] == ["image_2"]
    result = plan(PARENT, ctx)
    replay(ctx, result.transformations)
    html = BeautifulSoup(section(ctx, "solution")["html"], "html.parser")
    first, second, third = html.select("section")
    assert len(html.find_all("img")) == 2
    picture = first.find("img").find_parent("p")
    assert (
        picture.find_next_sibling("p").find("b").get_text()
        == "Приведем еще одно решение."
    )
    assert second.find("p").find("img") and not third.find("img")
    assert "sdamgia" not in str(html) and plan(PARENT, ctx).transformations == ()


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("change", ["id", "url", "target", "attribute"])
def test_every_native_repeated_reference_is_validated_before_any_is_discarded(
    index, change
):
    ctx = deepcopy(PARENT["context"])
    sec = section(ctx, "solution")
    soup = BeautifulSoup(sec["html"], "html.parser")
    image = soup.find_all("img")[index]
    key = {
        "id": "data-asset-id",
        "url": "src",
        "target": "data-transformation-target-id",
        "attribute": "data-unreviewed",
    }[change]
    image[key] = "foreign"
    sec["html"] = str(soup)
    before = deepcopy(ctx)
    with pytest.raises(ContentPlanError):
        plan(PARENT, ctx)
    assert ctx == before


@pytest.mark.parametrize(
    "change", ["duplicate_keys", "duplicate_metadata", "foreign_key", "owner"]
)
def test_repeated_figure_metadata_and_section_ownership_cannot_be_repaired_silently(
    change,
):
    ctx = deepcopy(PARENT["context"])
    sec = section(ctx, "solution")
    if change == "duplicate_keys":
        sec["asset_keys"] *= 2
    elif change == "duplicate_metadata":
        ctx["normalized_content"]["assets"].append(
            deepcopy(ctx["normalized_content"]["assets"][1])
        )
    else:
        soup = BeautifulSoup(sec["html"], "html.parser")
        if change == "foreign_key":
            for image in soup.find_all("img"):
                image["data-asset-key"] = "foreign"
            sec["html"] = str(soup)
        else:
            image = soup.find("img").extract()
            sec["html"] = str(soup)
            con = section(ctx, "condition")
            con["html"] += str(image)
            con["asset_keys"].append("image_2")
    with pytest.raises(ContentPlanError):
        plan(PARENT, ctx)


def test_another_family_cannot_repeat_a_native_solution_picture():
    case = next(c for c in CASES if c["task"] == "27925")
    ctx = deepcopy(case["context"])
    sec = section(ctx, "solution")
    soup = BeautifulSoup(sec["html"], "html.parser")
    soup.append(deepcopy(soup.find("img")))
    sec["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("a,b", [(0, 1), (1, 0), (5, 10), (5, 11)])
def test_degenerate_triangle_lengths_fail_closed(a, b):
    with pytest.raises(ContentPlanError):
        read_question(condition(a, b))


def test_right_triangle_keeps_all_four_methods_without_a_degenerate_center_triangle():
    ctx = right_context()
    m = read(ctx)
    result = plan(PARENT, ctx)
    html = solution_html(result)
    assert m.answer == 5 * sp.sqrt(2) / 2 and kind(m) == "right"
    assert len(generated(PARENT, ctx)) == 2
    verify(html, m)
    soup = BeautifulSoup(html, "html.parser")
    first, second, third = soup.select("section")
    assert first.find("b").get_text() == "Приведем еще одно решение."
    assert (
        "совпадает" in second.get_text()
        and "Из прямоугольного треугольника AOH" not in second.get_text()
    )
    assert "на одной прямой" in third.get_text()
    replay(ctx, result.transformations)
    assert section(ctx, "condition")["asset_keys"] == [CONDITION_KEY] and section(
        ctx, "solution"
    )["asset_keys"] == [DETAIL_KEY]
    assert plan(PARENT, ctx).transformations == ()


def xy(line, i):
    return tuple(float(line.get(a + str(i))) for a in ("x", "y"))


@pytest.mark.parametrize(
    "case", OBTUSE_CASES + [None], ids=["53821", "624071", "right"]
)
def test_dynamic_detail_has_the_actual_sides_radii_altitude_and_center_location(case):
    ctx = right_context() if case is None else case["context"]
    m = read(ctx)
    root = ET.fromstring(figure_svg(m, True))
    ring = root.find(_tag("circle"))
    o = tuple(float(ring.get(a)) for a in ("cx", "cy"))
    r = float(ring.get("r"))
    lines = {e.get("id"): e for e in root.findall(_tag("line"))}
    a, b, c = xy(lines["side-AB"], 1), xy(lines["side-AB"], 2), xy(lines["side-BC"], 2)
    h = xy(lines["height-CH"], 2)
    scale = r / float(m.answer)
    assert math.dist(a, b) / scale == pytest.approx(float(m.given[1]), abs=2e-6)
    assert math.dist(a, c) / scale == pytest.approx(float(m.given[0]), abs=2e-6)
    assert math.dist(b, c) == pytest.approx(math.dist(a, c), abs=2e-6)
    for p in (a, b, c):
        assert math.dist(p, o) == pytest.approx(r, abs=2e-6)
    assert a[1] == b[1] == h[1] and h[0] == o[0] and h[0] == c[0]
    assert xy(lines["radius-OA"], 1) == o and xy(lines["radius-OA"], 2) == a
    assert xy(lines["radius-CO"], 1) == c and xy(lines["radius-CO"], 2) == o
    assert lines["radius-OA"].get("stroke") == "#143B8F"
    if case is None:
        assert h == o and math.dist(a, b) == pytest.approx(2 * r)
        assert "merged-equal-0" in lines and "merged-equal-1" in lines
        assert (
            root.find(".//*[@id='label-H']") is not None
            and root.find(".//*[@id='label-O']") is not None
        )
    else:
        assert c[1] < h[1] < o[1] and not any(
            k.startswith("merged-equal") for k in lines
        )
    check_labels(root, [tuple(xy(e, i) for i in (1, 2)) for e in lines.values()])
    assert len(root.findall(_tag("g"))) == 7 and not list(root.iter(_tag("text")))
    original = ET.fromstring(source_bytes(DETAIL))
    old_groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    for name, old in zip(("A", "B", "C", "R_AO", "R_CO", "H", "O"), old_groups):
        glyph = root.find(".//*[@id='label-" + name + "']")
        assert [p.get("d") for p in glyph.iter(_tag("path"))] == [
            p.get("d") for p in old.iter(_tag("path"))
        ]
        x, y, w, height = _bounds(glyph)
        dx, dy = map(
            float,
            re.fullmatch(
                r"translate\(([^ ]+) ([^)]+)\)", glyph.get("transform")
            ).groups(),
        )
        x, y = x + dx, y + dy
        near = math.hypot(
            max(x - o[0], 0, o[0] - x - w), max(y - o[1], 0, o[1] - y - height)
        )
        far = max(math.dist(o, (bx, by)) for bx in (x, x + w) for by in (y, y + height))
        assert far < r - 0.5 or near > r + 0.5


def test_right_condition_is_an_actual_isosceles_right_triangle():
    root = ET.fromstring(figure_svg(read(right_context()), False))
    lines = {e.get("id"): e for e in root.findall(_tag("line"))}
    a, b, c = xy(lines["side-AB"], 1), xy(lines["side-AB"], 2), xy(lines["side-BC"], 2)
    assert math.dist(a, c) == pytest.approx(math.dist(b, c))
    assert sum((a[i] - c[i]) * (b[i] - c[i]) for i in (0, 1)) == pytest.approx(
        0, abs=2e-6
    )


def test_right_frozen_fake_roundtrip_materializes_two_roles_and_resumes_once():
    gateway = OfflineGateway(PARENT)
    gateway.context = right_context()
    record = prepared(PARENT, gateway)
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    assert apply_offline(PARENT, gateway, record)["status"] == "applied"
    assert len(gateway.uploads) == 2 and len(gateway.writes) == 1
    assert apply_offline(PARENT, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == 2 and len(gateway.writes) == 1


@pytest.mark.parametrize(
    "target",
    [
        "asset:" + CONDITION_KEY,
        "asset:" + DETAIL_KEY,
        "section:condition",
        "section:solution",
    ],
)
def test_missing_either_right_diagram_or_section_readback_is_failure(target):
    gateway = OfflineGateway(PARENT)
    gateway.context = right_context()
    record = prepared(PARENT, gateway)
    gateway.omit = next(
        t["transformation_target_id"]
        for t in record["transformations"]
        if t["transformation_target_id"].startswith(target)
    )
    assert apply_offline(PARENT, gateway, record)["status"] == "failed"


@pytest.mark.parametrize("change", ["condition", "svg", "reference"])
def test_frozen_drift_blocks_before_local_upload_or_write(change):
    case = OBTUSE_CASES[0]
    gateway = OfflineGateway(case)
    record = prepared(case, gateway)
    if change == "condition":
        section(gateway.context, "condition")["html"] += "Другие данные"
    elif change == "svg":
        record["generated_diagrams"][0]["svg_text"] += " "
    else:
        gateway.context["normalized_content"]["assets"][0]["asset_id"] = "foreign"
    assert apply_offline(case, gateway, record)["status"] in {"failed", "blocked"}
    assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("change", ["id", "url", "target"])
def test_every_generated_repeated_reference_is_checked(index, change):
    ctx = right_context()
    replay(ctx, plan(PARENT, ctx).transformations)
    sec = section(ctx, "solution")
    soup = BeautifulSoup(sec["html"], "html.parser")
    image = soup.find_all("img")[index]
    image[
        {
            "id": "data-asset-id",
            "url": "src",
            "target": "data-transformation-target-id",
        }[change]
    ] = "foreign"
    sec["html"] = str(soup)
    with pytest.raises(ContentPlanError):
        plan(PARENT, ctx)


@pytest.mark.parametrize("change", ["missing", "duplicate", "key", "hash", "id", "url"])
def test_generated_identities_are_verified_for_both_right_roles(change):
    ctx = right_context()
    assets = list(generated(PARENT, ctx))
    if change == "missing":
        assets.pop()
    elif change == "duplicate":
        assets.append(deepcopy(assets[0]))
    else:
        assets[0][
            {
                "key": "asset_key",
                "hash": "sha256",
                "id": "source_asset_id",
                "url": "url",
            }[change]
        ] = "" if change == "id" else "wrong"
    with pytest.raises(ContentPlanError):
        plan(PARENT, ctx, generated_solution_assets=tuple(assets))


def test_transition_across_all_three_center_locations_keeps_unique_operations():
    ctx = deepcopy(PARENT["context"])
    for a, b in [
        (13, 24),
        (5, r'<span data-inline-latex="5\sqrt{2}"></span>'),
        (40, 48),
    ]:
        sec = section(ctx, "condition")
        image = str(BeautifulSoup(sec["html"], "html.parser").find("img"))
        sec["html"] = image + condition(a, b)
        result = plan(PARENT, ctx)
        pairs = [
            (t["transformation_target_id"], t["operation"])
            for t in result.transformations
        ]
        assert len(pairs) == len(set(pairs))
        replay(ctx, result.transformations)
        assert (
            len(ctx["normalized_content"]["assets"]) == 2
            and plan(PARENT, ctx).transformations == ()
        )


@pytest.mark.parametrize("case", [PARENT, OBTUSE_CASES[0]], ids=["native", "generated"])
def test_losing_one_of_the_two_solution_occurrences_is_not_success(case):
    class MissingOccurrence(OfflineGateway):
        def apply_problem_transformations(self, identifier, transformations):
            response = super().apply_problem_transformations(
                identifier, transformations
            )
            sec = section(self.context, "solution")
            soup = BeautifulSoup(sec["html"], "html.parser")
            soup.find_all("img")[-1].decompose()
            sec["html"] = str(soup)
            return response

    gateway = MissingOccurrence(case)
    record = prepared(case, gateway)
    assert apply_offline(case, gateway, record)["status"] == "failed"


@pytest.mark.parametrize(
    "a,b",
    [
        (r'<span data-inline-latex="6+\sqrt{2}"></span>', 8),
        (13, r'<span data-inline-latex="24+\sqrt{2}"></span>'),
    ],
)
def test_composite_lengths_keep_all_four_methods_valid(a, b):
    ctx = deepcopy(PARENT["context"])
    sec = section(ctx, "condition")
    image = str(BeautifulSoup(sec["html"], "html.parser").find("img"))
    sec["html"] = image + condition(a, b)
    result = plan(PARENT, ctx)
    verify(solution_html(result), read(ctx))
    if kind(read(ctx)) == "obtuse":
        root = ET.fromstring(figure_svg(read(ctx), True))
        label = root.find(".//*[@id='label-H']")
        _, y, _, height = _bounds(label)
        _, dy = map(
            float,
            re.fullmatch(
                r"translate\(([^ ]+) ([^)]+)\)", label.get("transform")
            ).groups(),
        )
        line = root.find(".//*[@id='height-CH']")
        assert (
            y + dy > xy(line, 2)[1]
            and y + dy + height < xy(root.find(".//*[@id='radius-CO']"), 2)[1]
        )


@pytest.mark.parametrize("base", ["7,07107", "9,99999"])
def test_unresolvable_center_or_altitude_precision_fails_before_preparation(base):
    ctx = deepcopy(PARENT["context"])
    sec = section(ctx, "condition")
    image = str(BeautifulSoup(sec["html"], "html.parser").find("img"))
    sec["html"] = image + condition(5, base)
    before = deepcopy(ctx)
    with pytest.raises(ContentPlanError, match="precision"):
        plan(PARENT, ctx)
    assert ctx == before


@pytest.mark.parametrize("identifier", [None, ""])
def test_repeated_solution_with_missing_condition_identity_is_a_validation_error(
    identifier,
):
    ctx = deepcopy(PARENT["context"])
    sec = section(ctx, "condition")
    soup = BeautifulSoup(sec["html"], "html.parser")
    image = soup.find("img")
    if identifier is None:
        del image["data-asset-id"]
    else:
        image["data-asset-id"] = identifier
    sec["html"] = str(soup)
    before = deepcopy(ctx)
    with pytest.raises(ContentPlanError, match="identifier"):
        plan(PARENT, ctx)
    assert ctx == before
