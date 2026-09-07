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
    Asset("cos", "half", 0.5, "1/2", ("π/3", "5π/3")),
    Asset("cos", "sqrt2-over-2", sqrt(2) / 2, "√2/2", ("π/4", "7π/4")),
    Asset("cos", "sqrt3-over-2", sqrt(3) / 2, "√3/2", ("π/6", "11π/6")),
)
SIN = (
    Asset("sin", "minus-one", -1, "−1", ("3π/2",)),
    Asset("sin", "minus-sqrt3-over-2", -sqrt(3) / 2, "−√3/2", ("4π/3", "5π/3")),
    Asset("sin", "minus-sqrt2-over-2", -sqrt(2) / 2, "−√2/2", ("5π/4", "7π/4")),
    Asset("sin", "minus-half", -0.5, "−1/2", ("7π/6", "11π/6")),
    Asset("sin", "half", 0.5, "1/2", ("π/6", "5π/6")),
    Asset("sin", "sqrt2-over-2", sqrt(2) / 2, "√2/2", ("π/4", "3π/4")),
    Asset("sin", "sqrt3-over-2", sqrt(3) / 2, "√3/2", ("π/3", "2π/3")),
    Asset("sin", "one", 1, "1", ("π/2",)),
)
TAN = (
    Asset("tg", "minus-sqrt3", -sqrt(3), "−√3", ("5π/3",)),
    Asset("tg", "minus-one", -1, "−1", ("7π/4",)),
    Asset("tg", "minus-one-over-sqrt3", -1 / sqrt(3), "−1/√3", ("11π/6",)),
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


def bounded_angle_text(
    x: float,
    y: float,
    content: str,
    *,
    side: str,
) -> str:
    """Place an angle label near a point without clipping long fractions."""
    estimated_width = len(content) * 5.6
    if side == "start":
        if x + estimated_width <= 150:
            return text(x, y, content, anchor="start", blue=True)
        return text(150, y, content, anchor="end", blue=True)
    if side == "end":
        if x - estimated_width >= 3:
            return text(x, y, content, anchor="end", blue=True)
        return text(3, y, content, anchor="start", blue=True)
    raise ValueError(f"unsupported angle-label side: {side}")


def bounded_tangent_value(x: float, y: float, content: str) -> str:
    """Keep a tangent-value label inside the narrow portrait canvas."""
    estimated_width = len(content) * 5.6
    if x + estimated_width <= 150:
        return text(x, y, content, anchor="start", blue=True)
    return text(x - 10, y, content, anchor="end", blue=True)


def point(x: float, y: float) -> str:
    return f'<circle cx="{f(x)}" cy="{f(y)}" r="2.6" fill="{BLUE}" />'


def base(title: str, desc: str, body: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- Cleaned static derivative of Lessons Helper reference asset 1462b2e7-aa83-4c31-a512-412f3391c401. -->
<svg xmlns="http://www.w3.org/2000/svg" width="153" height="217" viewBox="0 0 153 217" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(desc)}</desc>
  <circle cx="{CX}" cy="{CY}" r="{R}" fill="none" {STROKE} />
  <line x1="8" y1="{CY}" x2="145" y2="{CY}" fill="none" {STROKE} />
  <line x1="{CX}" y1="40" x2="{CX}" y2="179" fill="none" {STROKE} />
{body}
</svg>
'''


def cos_svg(asset: Asset) -> str:
    x = CX + R * asset.value
    dy = R * sqrt(max(0, 1 - asset.value * asset.value))
    top, bottom = CY - dy, CY + dy
    top_angle, bottom_angle = asset.angles
    body = f'''  <!-- vertical dashed chord: cos value on both halves of the circle -->
  <line x1="{f(x)}" y1="{f(top)}" x2="{f(x)}" y2="{f(bottom)}" fill="none" {BLUE_STROKE} />
  {point(x, top)}
  {point(x, bottom)}
  {text(x, CY + 14, asset.label, blue=True)}
  {bounded_angle_text(x + 7, top - 5, top_angle, side="start")}
  {bounded_angle_text(x + 7, bottom + 10, bottom_angle, side="start")}
  {text(CX + R + 9, CY - 5, "1", anchor="start")}
  {text(CX - R - 8, CY - 5, "−1", anchor="end")}
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
    angle_y = y - 6
    value_y = y + 14 if y < CY else y - 14
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
    body = f'''  <!-- horizontal dashed chord: sin value on both halves of the circle -->
  <line x1="{f(left)}" y1="{f(y)}" x2="{f(right)}" y2="{f(y)}" fill="none" {BLUE_STROKE} />
  {points}
  {text(CX, value_y, asset.label, blue=True)}
  {angle_labels}
  {text(CX + 7, CY - R + 3, "1", anchor="start")}
  {text(CX + 7, CY + R + 9, "−1", anchor="start")}
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
    angle_y = circle_y - 6 if asset.value >= 0 else circle_y + 14
    body = f'''  <!-- radius to the circle and dashed extension to the tangent -->
  <line x1="{f(tangent_x)}" y1="8" x2="{f(tangent_x)}" y2="211" fill="none" {STROKE} />
  <line x1="{f(CX)}" y1="{f(CY)}" x2="{f(circle_x)}" y2="{f(circle_y)}" fill="none" {STROKE} />
  <line x1="{f(circle_x)}" y1="{f(circle_y)}" x2="{f(tangent_x)}" y2="{f(tangent_y)}" fill="none" {BLUE_STROKE} />
  {point(circle_x, circle_y)}
  {point(tangent_x, tangent_y)}
  <circle cx="{CX}" cy="{CY}" r="2.2" fill="{BLACK}" />
  {bounded_tangent_value(tangent_x + 6, tangent_y + 4, asset.label)}
  {bounded_angle_text(circle_x + 6, angle_y, asset.angles[0], side="start")}
  {text(tangent_x + 7, CY - 5, "1", anchor="start")}
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
