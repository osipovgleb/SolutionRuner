"""Coincident side-altitude figures retain source glyphs without a separate foot."""

import gzip
import hashlib
import itertools
import re
import xml.etree.ElementTree as ET
from importlib.resources import files

import pytest

from solution_runner.pipelines.triangles.isosceles.side_altitude_model import (
    read_question,
)
from solution_runner.pipelines.triangles.isosceles.side_altitude_svg import (
    _lettering,
    zero_svg,
)

SOURCE = "a41c52d0-9fcc-49cc-ace2-65c676d74aaf"
DIGEST = "575972a32c952064185bf37971e6c9bbfaf8f1173ade2910f5bdae2a57cdddb2"
NS = {"s": "http://www.w3.org/2000/svg"}


def raw_source():
    raw = gzip.decompress(
        files("solution_runner.pipelines.triangles.isosceles")
        .joinpath("assets/" + SOURCE + ".svgz")
        .read_bytes()
    )
    assert hashlib.sha256(raw).hexdigest() == DIGEST
    return raw


def question(frame, with_k):
    p, q, r = frame
    equal = "".join(sorted((p, r))) + "=" + "".join(sorted((q, r)))
    given = (
        equal + "=5"
        if with_k
        else equal + ", " + "".join(sorted((p, q))) + r"=10\sqrt{2}"
    )
    return read_question(
        "<p>В треугольнике ABC "
        + given
        + r", \cos "
        + q
        + p
        + r
        + r"=\frac{\sqrt{2}}{2}. Найдите высоту "
        + p
        + "H.</p>",
        "",
    )


@pytest.mark.parametrize(
    "frame", list(itertools.permutations("ABC")), ids=lambda f: "".join(f)
)
@pytest.mark.parametrize("with_k", [False, True])
def test_right_apex_height_and_merged_labels_have_correct_geometry_and_no_clipping(
    frame, with_k
):
    m = question(frame, with_k)
    raw = raw_source()
    root = ET.fromstring(zero_svg(m, raw, with_k))
    glyphs = _lettering(ET.fromstring(raw))
    lines = {n.get("id"): n for n in root.findall("s:line", NS)}

    def point(line, end):
        return tuple(float(line.get(c + str(end))) for c in "xy")

    p, q = point(lines["base"], 1), point(lines["base"], 2)
    r = point(lines["side-P-height"], 2)
    assert (
        point(lines["side-P-height"], 1) == p
        and point(lines["side-Q"], 1) == q
        and point(lines["side-Q"], 2) == r
    )
    u, v = (p[0] - r[0], p[1] - r[1]), (q[0] - r[0], q[1] - r[1])
    assert abs(u[0] * v[0] + u[1] * v[1]) < 1e-8
    assert abs(u[0] ** 2 + u[1] ** 2 - v[0] ** 2 - v[1] ** 2) < 1e-8
    assert "merged-equal-0" in lines and "merged-equal-1" in lines
    assert ("apex-altitude" in lines) == with_k
    if with_k:
        assert point(lines["apex-altitude"], 1) == r
        assert point(lines["apex-altitude"], 2) == ((p[0] + q[0]) / 2, p[1])
    left, top, width, height = map(float, root.get("viewBox").split())
    boxes = []
    labels = list(root.findall("s:g", NS))
    assert len(labels) == (5 if with_k else 4)
    for g in labels:
        name = g.get("id").removeprefix("label-")
        original = glyphs[name]
        assert [n.get("d") for n in g.findall(".//s:path", NS)] == [
            n.get("d") for n in original.findall(".//s:path", NS)
        ]
        dx, dy = map(
            float,
            re.fullmatch(r"translate\(([^ ]+) ([^)]+)\)", g.get("transform")).groups(),
        )
        rect = g.find(".//s:rect", NS)
        x, y = float(rect.get("x", 0)) + dx, float(rect.get("y", 0)) + dy
        w, h = float(rect.get("width")), float(rect.get("height"))
        assert left <= x < x + w <= left + width and top <= y < y + h <= top + height
        boxes.append((x, y, x + w, y + h))
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            assert min(a[2], b[2]) <= max(a[0], b[0]) or min(a[3], b[3]) <= max(
                a[1], b[1]
            )
    ids = [n.get("id") for n in root.iter() if n.get("id")]
    assert len(ids) == len(set(ids))
    assert not root.findall(".//s:text", NS)


def test_noncoincident_triangle_cannot_receive_a_right_apex_figure():
    from solution_runner.pipelines.core.errors import ContentPlanError

    m = read_question(
        r"<p>В треугольнике ABC AC=BC=5, \cos BAC=0{,}5. Найдите высоту AH.</p>", ""
    )
    with pytest.raises(ContentPlanError):
        zero_svg(m, raw_source(), True)
