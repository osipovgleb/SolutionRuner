"""Draw actual parallelogram heights with the parent's strokes and outlined letters."""

import math
import xml.etree.ElementTree as ET
from fractions import Fraction

from ...core.errors import ContentPlanError
from ...core.numbers import format_answer
from ...triangles.general.angle_label_positions import _position
from ...triangles.general.height_area_svg import _extension
from ...triangles.isosceles.basic_figures import canvas_svg
from ...triangles.isosceles.side_altitude_svg import _corner, _place, _style
from ...triangles.right.construction_svg import _bounds, _line, _tag
from .quantity_sources import source_bytes

SINE = "19b90e5e-1140-484f-8100-ead74bd010e9"
DETAIL = "f2ccbf6e-93b7-4dc0-96fa-ee00fe7aa8f2"


def points(model):
    a, b, sine = map(float, (model.a, model.b, model.sine))
    cosine = math.sqrt(max(0, 1 - sine * sine))
    p = {
        "A": (0, 0),
        "B": (a * cosine, -a * sine),
        "C": (b + a * cosine, -a * sine),
        "D": (b, 0),
    }
    if model.mode == "sine":
        p.update(H=(b * cosine**2, -b * sine * cosine), K=(b + a * cosine, 0))
    else:
        p.update(
            H=(a * cosine, 0),
            G=(b + a * cosine - b * cosine**2, -a * sine + b * sine * cosine),
        )
    xs, ys = zip(*p.values())
    extent = max(max(xs) - min(xs), max(ys) - min(ys))
    if not math.isfinite(extent) or extent <= 0:
        raise ContentPlanError("the parallelogram exceeds SVG precision")
    scale = max(260 / extent, 18 / min(a, b))
    if extent * scale > 1400 or min(a, b) * sine * scale < 1:
        raise ContentPlanError(
            "the distinct parallelogram heights collapse at SVG scale"
        )
    return {
        n: (12 + (x - min(xs)) * scale, 12 + (y - min(ys)) * scale)
        for n, (x, y) in p.items()
    }


def _labels(root, glyphs, model, p, black):
    shared = []
    for role, point in p.items():
        if model.mode == "transfer" and role == "H":
            continue
        match = next((g for g in shared if math.dist(g[0], point) < 1e-6), None)
        if match:
            match[1].append(role)
        else:
            shared.append((point, [role]))
    boxes = []
    for point, roles in shared:
        names = [model.name(n) for n in roles]
        widths = [_bounds(glyphs[n])[2] for n in names]
        height = max(_bounds(glyphs[n])[3] for n in names)
        width = sum(widths) + 10 * (len(names) - 1)
        x, y = point
        preferred = {
            "A": (x - width - 3, y + 3),
            "B": (x - width - 3, y - height - 3),
            "C": (x + 3, y - height - 3),
            "D": (x + 3, y + 3),
            "H": (x - width - 4, y + 12 if float(model.sine) < 0.4 else y - height / 2),
            "K": (x + 3, y + 3),
            "G": (x + 3, y + 3),
        }[roles[0]]
        x, y = _position(root, point, width, height, boxes, preferred)
        if len(names) > 1:
            boxes.append((x, y, width, height))
        for i, name in enumerate(names):
            _place(root, glyphs, name, x, y, boxes)
            x += widths[i]
            if i + 1 < len(names):
                for dy in (-1.5, 1.5):
                    _line(
                        root,
                        (x + 2, y + height / 2 + dy),
                        (x + 8, y + height / 2 + dy),
                        black,
                        f"coincident-{roles[0]}-{i}-{dy}",
                    )
                x += 10
    return boxes


def _numbers(root, model, p, boxes):
    values = {
        "AB": model.a,
        "AD": model.b,
        "BH": model.second_height,
        "BG": model.first_height,
    }
    placed = []
    for segment, amount in values.items():
        if amount.is_Rational:
            text = format_answer(Fraction(amount), allow_latex_fraction=True)
            if "\\" in text:
                text = str(Fraction(amount))
        else:
            text = (
                str(amount).replace("sqrt(", "√(").replace("**", "^").replace("*", "·")
            )
        first, second = (p[n] for n in segment)
        shared = next(
            (
                old
                for old in placed
                if any(
                    math.dist(first, ends[0]) < 1e-6
                    and math.dist(second, ends[1]) < 1e-6
                    for ends in (old[0], old[0][::-1])
                )
            ),
            None,
        )
        if shared is not None:
            if shared[1] != amount:
                raise ContentPlanError(
                    "distinct length labels collapse on one SVG segment"
                )
            label = shared[2]
            label.set(
                "data-segments",
                label.get("data-segments", label.get("id").removeprefix("value-"))
                + " "
                + segment,
            )
            continue
        font = 24 if len(text) <= 3 else 18
        fraction = 0.72 if segment == "BH" and len(text) > 3 else 0.5
        x, y = (first[i] + fraction * (second[i] - first[i]) for i in range(2))
        width, height = font * 0.5 * len(text) + 2, font * 1.1
        preferred = {
            "AB": (x - width - 5, y - height / 2),
            "AD": (x - width / 2, y + 5),
            "BH": (x + 5, y - height / 2),
            "BG": (x + 8, y - height - 4),
        }[segment]
        x, y = _position(root, (x, y), width, height, boxes, preferred)
        label = ET.SubElement(
            root,
            _tag("text"),
            {
                "id": "value-" + segment,
                "x": f"{x:.6f}",
                "y": f"{y + 0.84 * font:.6f}",
                "font-family": "Times New Roman, Times, serif",
                "font-size": str(font),
                "fill": "#000000",
            },
        )
        label.text = text
        placed.append(((first, second), amount, label))
        boxes.append((x, y, width, height))


def figure_svg(model):
    source = SINE if model.mode == "sine" else DETAIL
    original = ET.fromstring(source_bytes(source))
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    names = "ABHCDK" if model.mode == "sine" else "ABCDG"
    if len(groups) != (6 if model.mode == "sine" else 9):
        raise ContentPlanError("the audited height lettering changed")
    glyphs = dict(zip(names, groups[: len(names)]))
    lines = original.findall(_tag("line"))
    black = _style(
        next(line for line in lines if line.get("stroke") in {"#000000", "#0D0F0F"})
    )
    blue = _style(next(line for line in lines if line.get("stroke") == "#143B8F"))
    root = ET.Element(_tag("svg"), dict(original.attrib))
    p = points(model)
    heights = (
        [("D", "H", "AB"), ("C", "K", "AD")]
        if model.mode == "sine"
        else [("B", "H", "AD"), ("B", "G", "CD")]
    )
    for edge in ("AB", "BC", "CD", "DA"):
        ends = (p[edge[0]], p[edge[1]])
        if not any(
            all(math.dist(ends[i], p[n]) < 1e-6 for i, n in enumerate(order))
            for start, foot, _ in heights
            for order in ((start, foot), (foot, start))
        ):
            _line(root, *ends, black, "side-" + edge)
    dash = next(
        (
            e.get("stroke-dasharray")
            for e in original.iter(_tag("line"))
            if e.get("stroke-dasharray")
        ),
        "4 4",
    )
    for start, foot, side in heights:
        previous = len(root)
        _extension(root, p, side, foot, black)
        if len(root) != previous:
            if model.mode == "sine" and foot == "K":
                root[-1].attrib.pop("stroke-dasharray", None)
            elif model.mode == "transfer":
                root[-1].set("stroke-dasharray", dash)
        _line(root, p[start], p[foot], blue, "height-" + start + foot)
        vertex = max(side, key=lambda n: math.dist(p[n], p[foot]))
        size = min(
            7.688,
            0.35 * math.dist(p[start], p[foot]),
            0.35 * math.dist(p[vertex], p[foot]),
        )
        _corner(root, p[foot], p[start], p[vertex], blue, "right-" + foot, size=size)
    boxes = _labels(root, glyphs, model, p, black)
    if model.mode == "transfer":
        _numbers(root, model, p, boxes)
    xs, ys = zip(*p.values())
    root.set("viewBox", f"{min(xs)} {min(ys)} {max(xs) - min(xs)} {max(ys) - min(ys)}")
    return canvas_svg(root, boxes)
