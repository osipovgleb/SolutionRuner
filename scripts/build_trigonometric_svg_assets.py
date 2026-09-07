"""Prepare static trig diagrams by cleaning the reviewed Lessons Helper SVG.

This is an authoring tool only.  The runner never invokes it: it attaches the
committed, reviewed SVG files from ``pipelines/equations/assets/trigonometry``.
The source layout/palette comes from the downloaded reference SVG documented in
``docs/trigonometric-equations-runner.md``.  The script intentionally drops its
obsolete blue semicircle, old outlined text paths, duplicate points and clips.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).parents[1] / "src/solution_runner/pipelines/equations/assets/trigonometry"

# Coordinates/palette retained from the inspected source SVG.
CX, CY, R = 76.0, 109.5, 56.0
BLACK, BLUE = "#000000", "#00487E"
STROKE = 'stroke="#000000" stroke-width="0.75" stroke-linecap="round" stroke-linejoin="round" stroke-miterlimit="8"'
BLUE_STROKE = 'stroke="#00487E" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round" stroke-miterlimit="8" stroke-dasharray="5,3"'


@dataclass(frozen=True)
class Asset:
    function: str
    slug: str
    value: float
    label: str
    angles: tuple[str, ...]


COS = (
    Asset("cos", "minus-one", -1, "−1", ("π",)),
    Asset("cos", "minus-sqrt3-over-2", -sqrt(3) / 2, "−√3/2", ("5π/6", "−5π/6")),
    Asset("cos", "minus-sqrt2-over-2", -sqrt(2) / 2, "−√2/2", ("3π/4", "−3π/4")),
    Asset("cos", "minus-half", -0.5, "−1/2", ("2π/3", "−2π/3")),
    Asset("cos", "zero", 0, "0", ("π/2", "−π/2")),
    Asset("cos", "half", 0.5, "1/2", ("π/3", "−π/3")),
    Asset("cos", "sqrt2-over-2", sqrt(2) / 2, "√2/2", ("π/4", "−π/4")),
    Asset("cos", "sqrt3-over-2", sqrt(3) / 2, "√3/2", ("π/6", "−π/6")),
    Asset("cos", "one", 1, "1", ("0",)),
)
SIN = (
    Asset("sin", "minus-one", -1, "−1", ("−π/2",)),
    Asset("sin", "minus-sqrt3-over-2", -sqrt(3) / 2, "−√3/2", ("−2π/3", "−π/3")),
    Asset("sin", "minus-sqrt2-over-2", -sqrt(2) / 2, "−√2/2", ("−3π/4", "−π/4")),
    Asset("sin", "minus-half", -0.5, "−1/2", ("−5π/6", "−π/6")),
    Asset("sin", "zero", 0, "0", ("0", "π")),
    Asset("sin", "half", 0.5, "1/2", ("π/6", "5π/6")),
    Asset("sin", "sqrt2-over-2", sqrt(2) / 2, "√2/2", ("π/4", "3π/4")),
    Asset("sin", "sqrt3-over-2", sqrt(3) / 2, "√3/2", ("π/3", "2π/3")),
    Asset("sin", "one", 1, "1", ("π/2",)),
)
TAN = (
    Asset("tg", "zero", 0, "0", ("0",)),
    Asset("tg", "minus-sqrt3", -sqrt(3), "−√3", ("−π/3",)),
    Asset("tg", "minus-one", -1, "−1", ("−π/4",)),
    Asset("tg", "minus-one-over-sqrt3", -1 / sqrt(3), "−1/√3", ("−π/6",)),
    Asset("tg", "one-over-sqrt3", 1 / sqrt(3), "1/√3", ("π/6",)),
    Asset("tg", "one", 1, "1", ("π/4",)),
    Asset("tg", "sqrt3", sqrt(3), "√3", ("π/3",)),
)


def f(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def text(
    x: float,
    y: float,
    content: str,
    *,
    anchor: str = "middle",
    blue: bool = False,
    size: float = 10,
) -> str:
    color = BLUE if blue else BLACK
    # The downloaded reference has outlined glyphs and does not carry a font
    # family. Use an installed, open Cyrillic-capable font and a deterministic
    # fallback instead of naming a font that may not exist in the runner image.
    return (
        f'<text x="{f(x)}" y="{f(y)}" fill="{color}" '
        f'font-family="Liberation Sans, DejaVu Sans, sans-serif" '
        f'font-size="{f(size)}" text-anchor="{anchor}">{escape(content)}</text>'
    )


def angle_text(
    x: float,
    y: float,
    content: str,
    *,
    anchor: str,
) -> str:
    """Render a compact stacked fraction rather than slash notation."""
    if "/" not in content:
        return text(x, y, content, anchor=anchor, blue=True)
    numerator, denominator = content.split("/", 1)
    negative = numerator.startswith("−")
    if negative:
        numerator = numerator[1:]
    width = max(10, len(numerator) * 5.5)
    left = x + 5 if negative and anchor == "start" else x if anchor == "start" else x - width
    center = left + width / 2
    minus = (
        f'<text x="{f(left - 4)}" y="{f(y + 3)}" text-anchor="middle">−</text>'
        if negative
        else ""
    )
    return (
        f'<g data-angle="{escape(content)}" fill="{BLUE}" '
        'font-family="Liberation Sans, DejaVu Sans, sans-serif" font-size="10">'
        f'{minus}'
        f'<text x="{f(center)}" y="{f(y - 4)}" text-anchor="middle">{escape(numerator)}</text>'
        f'<line x1="{f(left)}" y1="{f(y - 1)}" x2="{f(left + width)}" y2="{f(y - 1)}" stroke="{BLUE}" stroke-width="0.7"/>'
        f'<text x="{f(center)}" y="{f(y + 8)}" text-anchor="middle">{escape(denominator)}</text></g>'
    )


def bounded_angle_text(x: float, y: float, content: str, *, side: str) -> str:
    """Place an angle label near a point without clipping a stacked fraction."""
    width = max(14, len(content.split("/", 1)[0]) * 5.5) if "/" in content else len(content) * 5.6
    if side == "start":
        return angle_text(x if x + width <= 150 else 150, y, content, anchor="start" if x + width <= 150 else "end")
    if side == "end":
        return angle_text(x if x - width >= 3 else 3, y, content, anchor="end" if x - width >= 3 else "start")
    raise ValueError(f"unsupported angle-label side: {side}")


def bounded_tangent_value(x: float, y: float, content: str) -> str:
    """Keep a tangent-value label inside the narrow portrait canvas."""
    estimated_width = len(content) * 5.6
    if x + estimated_width <= 150:
        return angle_text(x, y, content, anchor="start")
    return angle_text(x - 10, y, content, anchor="end")


def point(x: float, y: float) -> str:
    return f'<circle cx="{f(x)}" cy="{f(y)}" r="2.6" fill="{BLUE}" />'


def base(title: str, desc: str, body: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- Cleaned static derivative of Lessons Helper reference asset 1462b2e7-aa83-4c31-a512-412f3391c401. -->
<svg xmlns="http://www.w3.org/2000/svg" width="153" height="217" viewBox="0 0 153 217" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(desc)}</desc>
  <defs><marker id="axis-arrow" markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto"><path d="M0,0 L5,2.5 L0,5 Z" fill="{BLACK}"/></marker></defs>
  <circle cx="{CX}" cy="{CY}" r="{R}" fill="none" {STROKE} />
  <line x1="8" y1="{CY}" x2="145" y2="{CY}" fill="none" {STROKE} marker-end="url(#axis-arrow)" />
  <line x1="{CX}" y1="179" x2="{CX}" y2="40" fill="none" {STROKE} marker-end="url(#axis-arrow)" />
{body}
</svg>
'''


def cos_svg(asset: Asset) -> str:
    x = CX + R * asset.value
    dy = R * sqrt(max(0, 1 - asset.value * asset.value))
    top, bottom = CY - dy, CY + dy
    # For a negative cosine the coordinate line is left of the circle centre.
    # Put both angle captions to its left, so they do not cover the circle.
    angle_side = "end" if x < CX or asset.slug == "zero" else "start"
    angle_x = x - 7 if angle_side == "end" else x + 7
    # Mark the projection on the cosine axis separately.  At ±1 it is the
    # same point as the circle intersection; at zero it is the centre.
    axis_point = "" if asset.value in {-1, 1} else point(x, CY)
    if len(asset.angles) == 1:
        angle_labels = bounded_angle_text(angle_x, top - 12, asset.angles[0], side=angle_side)
        points = point(x, top)
    else:
        top_angle, bottom_angle = asset.angles
        angle_labels = "\n  ".join(
            (
                bounded_angle_text(angle_x, top - 12, top_angle, side=angle_side),
                bounded_angle_text(angle_x, bottom + 16, bottom_angle, side=angle_side),
            )
        )
        points = f"{point(x, top)}\n  {point(x, bottom)}"
    if axis_point:
        points = f"{points}\n  {axis_point}"
    # These two reviewed √2/2 diagrams place the value to the left of the
    # coordinate line, keeping it clear of the horizontal-axis caption.
    value_side = (
        "start"
        if asset.slug == "minus-sqrt2-over-2"
        else "end"
        if x < CX or asset.slug in {"sqrt2-over-2", "sqrt3-over-2"}
        else "start"
    )
    value_x = x + 8 if value_side == "start" else x - 8
    revision_marker = "  <!-- reviewed label placement -->\n" if asset.slug == "minus-sqrt2-over-2" else ""
    body = f'''{revision_marker}  <!-- full dashed coordinate line shows the cosine value beyond the circle -->
  <line x1="{f(x)}" y1="8" x2="{f(x)}" y2="211" fill="none" {BLUE_STROKE} />
  {points}
  {angle_text(value_x, CY + 15, asset.label, anchor=value_side)}
  {angle_labels}
  {text(149, CY + 14, "cos", anchor="end", size=9)}
  {text(CX + 5, CY - R - 20, "sin", anchor="start", size=9)}
'''
    return base(
        f"cos t = {asset.label}",
        "Единичная окружность: точки пересечения косинуса подписаны точными углами.",
        body,
    )


def sin_svg(asset: Asset) -> str:
    y = CY - R * asset.value
    dx = R * sqrt(max(0, 1 - asset.value * asset.value))
    left, right = CX - dx, CX + dx
    angle_y = y + 14 if asset.slug == "one" else y - 14 if y <= CY else y + 14
    # These reviewed negative sine values are captioned above their horizontal
    # coordinate line; the top endpoint uses the opposite side of OY.
    value_above_line = asset.slug in {
        "minus-one",
        "minus-sqrt2-over-2",
        "minus-sqrt3-over-2",
    }
    value_below_line = asset.slug in {"sqrt2-over-2", "sqrt3-over-2"}
    value_y = y + 18 if value_below_line else y - 9 if y <= CY or value_above_line else y + 18
    value_side = "end" if asset.slug == "one" else "start"
    value_x = CX - 8 if value_side == "end" else CX + 8
    if len(asset.angles) == 1:
        angle_labels = bounded_angle_text(CX + 6, angle_y, asset.angles[0], side="start")
    else:
        angle_labels = "\n  ".join(
            (
                bounded_angle_text(left - 5, angle_y, asset.angles[0], side="end"),
                bounded_angle_text(right + 5, angle_y, asset.angles[-1], side="start"),
            )
        )
    if left == right:
        points = point(left, y)
    else:
        points = f"{point(left, y)}\n  {point(right, y)}"
    # Mark the projection on the sine axis separately.  The extreme points
    # already lie on that axis; zero needs a visible centre point too.
    if asset.value not in {-1, 1}:
        points = f"{points}\n  {point(CX, y)}"
    body = f'''  <!-- full dashed coordinate line shows the sine value beyond the circle -->
  <line x1="8" y1="{f(y)}" x2="145" y2="{f(y)}" fill="none" {BLUE_STROKE} />
  {points}
  {angle_text(value_x, value_y, asset.label, anchor=value_side)}
  {angle_labels}
  {text(149, CY + 14, "cos", anchor="end", size=9)}
  {text(CX + 5, CY - R - 20, "sin", anchor="start", size=9)}
'''
    return base(
        f"sin t = {asset.label}",
        "Единичная окружность: точки пересечения синуса подписаны точными углами.",
        body,
    )


def tg_svg(asset: Asset) -> str:
    tangent_x = CX + R
    denominator = sqrt(1 + asset.value * asset.value)
    circle_x = CX + R / denominator
    circle_y = CY - R * asset.value / denominator
    tangent_y = CY - R * asset.value
    # Put the angle caption close to its point, inside the circle and below
    # the blue dashed segment.  The offset leaves a visible gap to both the
    # point and the circle stroke.
    normal_length = sqrt(1 + asset.value * asset.value)
    # For ±π/6 the circle is nearly tangent to the caption.  Move those
    # captions a little further inward; the remaining variants may stay
    # close to their marked points without touching the circumference.
    inner_radius = R * (0.70 if abs(asset.value) == 1 / sqrt(3) else 0.82)
    angle_x = CX + inner_radius / normal_length + 8 * asset.value / normal_length
    angle_y = CY - inner_radius * asset.value / normal_length + 8 / normal_length + 4
    angle_side = "start" if asset.value >= 0 else "end"
    if asset.value == 0:
        angle_x, angle_y, angle_side = circle_x - 10, circle_y + 18, "end"
    body = f'''  <!-- dashed tangent value runs from the centre to the tangent -->
  <line x1="{f(tangent_x)}" y1="211" x2="{f(tangent_x)}" y2="8" fill="none" {STROKE} marker-end="url(#axis-arrow)" />
  <line x1="{f(CX)}" y1="{f(CY)}" x2="{f(tangent_x)}" y2="{f(tangent_y)}" fill="none" {BLUE_STROKE} />
  {point(circle_x, circle_y)}
  {point(tangent_x, tangent_y)}
  <circle cx="{CX}" cy="{CY}" r="2.2" fill="{BLACK}" />
  {angle_text(149, tangent_y + 4, asset.label, anchor="end")}
  {bounded_angle_text(angle_x, angle_y, asset.angles[0], side=angle_side)}
  {text(149, 28, "tg", anchor="end", size=9)}
  {text(CX + 5, CY - R - 20, "sin", anchor="start", size=9)}
  {text(149, CY + 14, "cos", anchor="end", size=9)}
'''
    return base(
        f"tg t = {asset.label}",
        "Единичная окружность с касательной: точка пересечения и угол подписаны точно.",
        body,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    builders = {"cos": cos_svg, "sin": sin_svg, "tg": tg_svg}
    for asset in COS + SIN + TAN:
        path = OUT / f"{asset.function}-{asset.slug}.svg"
        path.write_text(builders[asset.function](asset), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Статические SVG для табличных тригонометрических значений\n\n"
        "Это очищенные производные эталонного SVG из Lessons Helper. Они создаются "
        "скриптом автора один раз и затем прикрепляются раннером как готовые файлы; "
        "во время обработки задач SVG не генерируются. Точки пересечения подписаны "
        "точными углами, а подписи используют Liberation Sans с запасным DejaVu Sans.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
