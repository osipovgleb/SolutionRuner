"""Vectorize three-day raster temperature charts with unequal axis scales."""

from __future__ import annotations

import html
import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import cv2
import numpy as np
from scipy.interpolate import PchipInterpolator

from . import graph_png_to_svg_by_contrast as graph_base
from .temperature_graph_grid import _grid_lines
from .temperature_graph_labels import (
    _MONTHS,
    day_labels_from_ocr,
    recover_y_axis_labels,
    requested_date_from_condition,
)


@dataclass(frozen=True)
class TemperatureGraphAnalysis:
    """Hold verified chart geometry, scale, dates, trace, and requested result."""

    plot_left: float
    plot_top: float
    plot_right: float
    plot_bottom: float
    x_grid_step: float
    y_grid_step: float
    horizontal_grid_count: int
    vertical_grid_count: int
    degrees_per_pixel: float
    temperature_intercept: float
    day_labels: tuple[date, date, date]
    requested_day_index: int
    maximum_temperature: int
    curve_points: tuple[tuple[float, float], ...]
    chromatic_curve: bool


@dataclass(frozen=True)
class TemperatureGraphConversion:
    """Expose verified artifacts and analysis to an MCP-facing runner."""

    svg_path: Path
    diagnostics_path: Path
    analysis: TemperatureGraphAnalysis
    alt_text: str


OcrReader = Callable[
    [np.ndarray, tuple[float, ...], Path],
    tuple[tuple[str, ...], str],
]


def _cubic_curve_path(points: list[tuple[float, float]]) -> str:
    """Return a shape-preserving cubic SVG path through every mapped point."""

    coordinates = np.asarray(points, dtype=np.float64)
    if coordinates.ndim != 2 or coordinates.shape[1] != 2 or len(coordinates) < 2:
        raise ValueError("temperature curve requires at least two mapped points")
    xs = coordinates[:, 0]
    ys = coordinates[:, 1]
    if np.any(np.diff(xs) <= 0):
        raise ValueError("mapped temperature curve x-coordinates must increase")
    interpolator = PchipInterpolator(xs, ys)
    slopes = np.asarray(interpolator.derivative()(xs), dtype=np.float64)
    commands = [f"M{xs[0]:.2f},{ys[0]:.2f}"]
    for index in range(len(coordinates) - 1):
        x0, y0 = coordinates[index]
        x1, y1 = coordinates[index + 1]
        third = (x1 - x0) / 3.0
        commands.append(
            "C"
            f"{x0 + third:.2f},{y0 + slopes[index] * third:.2f} "
            f"{x1 - third:.2f},{y1 - slopes[index + 1] * third:.2f} "
            f"{x1:.2f},{y1:.2f}"
        )
    return " ".join(commands)


def _curve_component(
    image: np.ndarray,
    vertical: tuple[float, ...],
    horizontal: tuple[float, ...],
) -> tuple[np.ndarray, bool]:
    """Return the dominant full-width curve component inside the plot."""

    left, right = round(vertical[0]), round(vertical[-1])
    top, bottom = round(horizontal[0]), round(horizontal[-1])
    rgb = image[:, :, :3]
    crop = rgb[top : bottom + 1, left : right + 1]
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    chromatic = bool(np.mean(hsv[:, :, 1] >= 45) >= 0.003)
    if chromatic:
        foreground = ((hsv[:, :, 1] >= 45) & (hsv[:, :, 2] <= 245)).astype(np.uint8)
    else:
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        foreground = (gray < 80).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    candidates = []
    for index in range(1, count):
        width = int(stats[index, cv2.CC_STAT_WIDTH])
        area = int(stats[index, cv2.CC_STAT_AREA])
        if width >= (right - left) * 0.82:
            candidates.append((area, index))
    if not candidates:
        raise ValueError("full-width temperature curve was not found")
    _, selected = max(candidates)
    yy, xx = np.where(labels == selected)
    points: list[tuple[float, float]] = []
    for x in range(int(xx.min()), int(xx.max()) + 1):
        ys = yy[xx == x]
        if ys.size:
            points.append((float(x + left), float(np.median(ys) + top)))
    if len(points) < (right - left) * 0.80:
        raise ValueError("temperature curve coverage is incomplete")
    return np.asarray(points, dtype=np.float64), chromatic


def _temperature_scale(
    labels: tuple[tuple[float, float], ...],
) -> tuple[float, float]:
    """Fit and verify the affine pixel-y to temperature mapping."""

    if len(labels) < 3:
        raise ValueError("at least three y-axis labels are required")
    ys = np.asarray([item[0] for item in labels], dtype=np.float64)
    values = np.asarray([item[1] for item in labels], dtype=np.float64)
    slope, intercept = np.polyfit(ys, values, 1)
    residual = np.max(np.abs(values - (slope * ys + intercept)))
    if slope >= 0 or residual > 0.12:
        raise ValueError("y-axis labels do not define one decreasing linear scale")
    return float(slope), float(intercept)


def analyze_temperature_graph(
    image: np.ndarray,
    *,
    y_axis_labels: tuple[tuple[float, float], ...],
    day_labels: tuple[date, date, date],
    requested_date: date,
) -> TemperatureGraphAnalysis:
    """Recover one chart and independently calculate its requested daily maximum."""

    vertical, horizontal = _grid_lines(image)
    curve, chromatic = _curve_component(image, vertical, horizontal)
    slope, intercept = _temperature_scale(y_axis_labels)
    try:
        requested_day_index = day_labels.index(requested_date)
    except ValueError as exc:
        raise ValueError("requested date is absent from chart labels") from exc
    day_left = vertical[requested_day_index * 4]
    day_right = vertical[(requested_day_index + 1) * 4]
    day_curve = curve[(curve[:, 0] >= day_left) & (curve[:, 0] <= day_right)]
    if len(day_curve) < 20:
        raise ValueError("requested day has insufficient curve evidence")
    peak_y = float(np.percentile(day_curve[:, 1], 1.0))
    maximum = slope * peak_y + intercept
    rounded = round(maximum)
    if abs(maximum - rounded) > 0.30:
        raise ValueError(f"daily maximum is off the integer scale: {maximum:.3f}")
    return TemperatureGraphAnalysis(
        plot_left=vertical[0],
        plot_top=horizontal[0],
        plot_right=vertical[-1],
        plot_bottom=horizontal[-1],
        x_grid_step=float(np.median(np.diff(vertical))),
        y_grid_step=float(np.median(np.diff(horizontal))),
        horizontal_grid_count=len(horizontal),
        vertical_grid_count=len(vertical),
        degrees_per_pixel=slope,
        temperature_intercept=intercept,
        day_labels=day_labels,
        requested_day_index=requested_day_index,
        maximum_temperature=rounded,
        curve_points=tuple((float(x), float(y)) for x, y in curve),
        chromatic_curve=chromatic,
    )


def _read_with_tesseract_js(
    image: np.ndarray,
    horizontal_lines: tuple[float, ...],
    output_dir: Path,
) -> tuple[tuple[str, ...], str]:
    """Read isolated tick and date crops with one local Tesseract.js worker."""

    vertical, _ = _grid_lines(image)
    left = round(vertical[0])
    bottom = round(horizontal_lines[-1])
    crop_dir = output_dir / "ocr"
    crop_dir.mkdir(parents=True, exist_ok=True)
    tick_paths: list[str] = []
    for index, pixel_y in enumerate(horizontal_lines):
        y = round(pixel_y)
        crop = image[
            max(0, y - 7) : min(image.shape[0], y + 7), max(0, left - 46) : left - 1
        ]
        enlarged = cv2.resize(crop, None, fx=5, fy=5, interpolation=cv2.INTER_CUBIC)
        path = crop_dir / f"tick-{index:03d}.png"
        cv2.imwrite(str(path), cv2.cvtColor(enlarged, cv2.COLOR_RGBA2BGRA))
        tick_paths.append(str(path))
    date_crop = image[
        min(image.shape[0] - 1, bottom + 3) :,
        max(0, left - 12) : min(image.shape[1], round(vertical[-1]) + 14),
    ]
    date_path = crop_dir / "dates.png"
    enlarged_dates = cv2.resize(
        date_crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
    )
    cv2.imwrite(str(date_path), cv2.cvtColor(enlarged_dates, cv2.COLOR_RGBA2BGRA))
    helper = Path(__file__).with_name("temperature_graph_ocr.js")
    completed = subprocess.run(
        ["node", str(helper)],
        input=json.dumps({"tick_paths": tick_paths, "date_path": str(date_path)}),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError(
            "Tesseract.js failed: " + " ".join(completed.stderr.split())[:500]
        )
    payload = json.loads(completed.stdout)
    ticks = payload.get("ticks")
    dates = payload.get("dates")
    if (
        not isinstance(ticks, list)
        or len(ticks) != len(horizontal_lines)
        or not isinstance(dates, str)
    ):
        raise ValueError("Tesseract.js returned an invalid crop result")
    return tuple(str(value) for value in ticks), dates


def convert_temperature_graph(
    source: str | Path,
    output_dir: Path,
    *,
    condition_text: str,
    expected_answer: int,
    ocr_reader: OcrReader = _read_with_tesseract_js,
) -> TemperatureGraphConversion:
    """Convert one chart only after OCR, date, and answer verification succeed."""

    rgba, _ = graph_base.load_image(str(source))
    _, horizontal = _grid_lines(rgba)
    output_dir.mkdir(parents=True, exist_ok=True)
    tick_tokens, date_text = ocr_reader(rgba, horizontal, output_dir)
    y_labels = recover_y_axis_labels(horizontal, tick_tokens)
    requested = requested_date_from_condition(condition_text)
    day_labels = day_labels_from_ocr(date_text, requested)
    analysis = analyze_temperature_graph(
        rgba,
        y_axis_labels=y_labels,
        day_labels=day_labels,
        requested_date=requested,
    )
    if analysis.maximum_temperature != expected_answer:
        raise ValueError(
            "computed maximum "
            f"{analysis.maximum_temperature} does not match expected answer {expected_answer}"
        )
    stem = Path(source).stem
    svg_path = output_dir / f"{stem}.svg"
    diagnostics_path = output_dir / f"{stem}.json"
    svg_path.write_text(render_temperature_graph_svg(analysis), encoding="utf-8")
    diagnostics_path.write_text(
        json.dumps(
            {
                "algorithm": "calendar-temperature-graph-v1",
                "source": str(source),
                "maximum_temperature": analysis.maximum_temperature,
                "requested_day_index": analysis.requested_day_index,
                "day_labels": [day.isoformat() for day in analysis.day_labels],
                "x_grid_step": analysis.x_grid_step,
                "y_grid_step": analysis.y_grid_step,
                "degrees_per_pixel": analysis.degrees_per_pixel,
                "chromatic_curve": analysis.chromatic_curve,
                "curve_point_count": len(analysis.curve_points),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    first, last = analysis.day_labels[0], analysis.day_labels[-1]
    alt_text = (
        f"График температуры с {first.day} {_MONTHS[first.month]} "
        f"по {last.day} {_MONTHS[last.month]}"
    )
    return TemperatureGraphConversion(svg_path, diagnostics_path, analysis, alt_text)


def render_temperature_graph_svg(analysis: TemperatureGraphAnalysis) -> str:
    """Render the verified chart in the source prototype's restrained blue style."""

    source_width = analysis.plot_right - analysis.plot_left
    source_height = analysis.plot_bottom - analysis.plot_top
    left, top = 58.0, 12.0
    plot_width = (analysis.vertical_grid_count - 1) * 34.0
    plot_height = max(150.0, (analysis.horizontal_grid_count - 1) * 10.0)
    right, bottom = left + plot_width, top + plot_height

    def map_point(point: tuple[float, float]) -> tuple[float, float]:
        """Map one source pixel point into the normalized SVG plot."""

        x, y = point
        return (
            left + (x - analysis.plot_left) / source_width * plot_width,
            top + (y - analysis.plot_top) / source_height * plot_height,
        )

    sampled = analysis.curve_points
    mapped = [map_point(point) for point in sampled]
    path = _cubic_curve_path(mapped)
    rows = []
    minor_temperature_step = (
        round(abs(analysis.degrees_per_pixel * analysis.y_grid_step) * 2) / 2
    )
    if minor_temperature_step <= 0:
        raise ValueError("rendered temperature step is not positive")
    top_temperature = (
        round(
            (
                analysis.degrees_per_pixel * analysis.plot_top
                + analysis.temperature_intercept
            )
            / minor_temperature_step
        )
        * minor_temperature_step
    )
    label_stride = 1 if analysis.chromatic_curve else 2
    for index in range(analysis.horizontal_grid_count):
        y = top + index * plot_height / max(1, analysis.horizontal_grid_count - 1)
        value = top_temperature - index * minor_temperature_step
        label = (
            f'<text x="{left - 8:.2f}" y="{y + 3.5:.2f}" text-anchor="end">{value:g}</text>'
            if index % label_stride == 0
            else ""
        )
        rows.append(
            f'<line x1="{left:.2f}" y1="{y:.2f}" x2="{right:.2f}" y2="{y:.2f}" '
            f'stroke="#aaa" stroke-width=".7"/>{label}'
        )
    columns = []
    for index in range(analysis.vertical_grid_count):
        x = left + index * plot_width / max(1, analysis.vertical_grid_count - 1)
        columns.append(
            f'<line x1="{x:.2f}" y1="{top:.2f}" x2="{x:.2f}" y2="{bottom:.2f}" '
            f'stroke="#aaa" stroke-width=".7"/>'
            f'<text x="{x:.2f}" y="{bottom + 18:.2f}" text-anchor="middle">{(index * 6) % 24}:00</text>'
        )
    dates = []
    for index, day in enumerate(analysis.day_labels):
        x = left + (index * 4 + 2) * plot_width / max(
            1, analysis.vertical_grid_count - 1
        )
        dates.append(
            f'<text x="{x:.2f}" y="{bottom + 40:.2f}" text-anchor="middle" font-weight="700">'
            f"{day.day} {html.escape(_MONTHS[day.month])}</text>"
        )
    width, height = right + 18.0, bottom + 52.0
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.2f} {height:.2f}">\n'
        '<rect width="100%" height="100%" fill="white"/>\n'
        '<g font-family="serif" font-size="12" fill="#111">\n'
        f"<g>{''.join(rows)}{''.join(columns)}</g>\n"
        f'<text x="8" y="{(top + bottom) / 2:.2f}" font-style="italic">t, °C</text>\n'
        f'<path d="{path}" fill="none" stroke="#2f63ad" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"/>\n'
        f"{''.join(dates)}\n</g>\n</svg>\n"
    )
