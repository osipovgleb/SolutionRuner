"""Find the independently scaled temperature chart grid axes."""

from collections.abc import Iterable

import cv2
import numpy as np

from . import graph_png_to_svg_by_contrast as graph_base


def _longest_regular_run(values: Iterable[float], step: float) -> tuple[float, ...]:
    """Return the longest observed sequence separated by one fitted lattice step."""

    ordered = tuple(sorted(float(value) for value in values))
    tolerance = max(1.1, step * 0.12)
    best: tuple[float, ...] = ()
    for start_index, first in enumerate(ordered):
        run = [first]
        cursor = first
        for value in ordered[start_index + 1 :]:
            delta = value - cursor
            if abs(delta - step) <= tolerance:
                run.append(value)
                cursor = value
            elif delta > step + tolerance:
                break
        if len(run) > len(best):
            best = tuple(run)
    return best


def _grid_lines(image: np.ndarray) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Detect independent horizontal and vertical chart lattices."""

    if image.ndim != 3 or image.shape[2] not in {3, 4}:
        raise ValueError("temperature chart must be an RGB or RGBA image")
    rgba = image if image.shape[2] == 4 else cv2.cvtColor(image, cv2.COLOR_RGB2RGBA)
    darkness = graph_base.effective_darkness(rgba)

    def strongest_axis(*, vertical_axis: bool) -> tuple[float, ...]:
        """Choose the threshold exposing the longest coherent lattice run."""

        axis_size = image.shape[1 if vertical_axis else 0]
        candidates: list[tuple[float, ...]] = []
        for threshold in (0.20, 0.18, 0.16, 0.14):
            centers = graph_base.projection_line_centers(
                darkness,
                vertical=vertical_axis,
                foreground_threshold=threshold,
            )
            try:
                fitted = graph_base.fit_grid_axis(centers, axis_size)
            except ValueError:
                continue
            run = _longest_regular_run(centers, fitted.step)
            if run:
                candidates.append(run)
        if not candidates:
            raise ValueError("regular chart lattice was not found")
        return max(candidates, key=len)

    vertical = strongest_axis(vertical_axis=True)
    horizontal = strongest_axis(vertical_axis=False)
    if len(vertical) < 13:
        raise ValueError(f"calendar chart has only {len(vertical)} vertical grid lines")
    if len(horizontal) < 6:
        raise ValueError(
            f"temperature chart has only {len(horizontal)} horizontal grid lines"
        )
    return vertical, horizontal
