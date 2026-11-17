"""Fit smooth graph paths and serialize their SVG geometry."""

from __future__ import annotations

import numpy as np


def _fmt(value: float, digits: int = 2) -> str:
    """Format a stable compact SVG number."""
    rounded = round(float(value), digits)
    if abs(rounded - round(rounded)) < 10 ** (-digits):
        return str(round(rounded))
    return f"{rounded:.{digits}f}".rstrip("0").rstrip(".")


def _polyline_path(points: np.ndarray) -> str:
    """Build a straight-segment SVG path through all knots."""
    commands = [f"M{_fmt(points[0, 0])} {_fmt(points[0, 1])}"]
    commands.extend(f"L{_fmt(x)} {_fmt(y)}" for x, y in points[1:])
    return " ".join(commands)


def _pchip_slopes(points: np.ndarray) -> np.ndarray:
    """Compute shape-preserving Hermite slopes for knots with increasing x coordinates."""
    x_values = points[:, 0].astype(np.float64)
    y_values = points[:, 1].astype(np.float64)
    intervals = np.diff(x_values)
    if np.any(intervals <= 0.0):
        raise ValueError("curve_knots_must_have_increasing_x")
    secants = np.diff(y_values) / intervals
    slopes = np.zeros(len(points), dtype=np.float64)
    if len(points) == 2:
        slopes[:] = secants[0]
        return slopes

    for index in range(1, len(points) - 1):
        left = secants[index - 1]
        right = secants[index]
        if left == 0.0 or right == 0.0 or left * right <= 0.0:
            slopes[index] = 0.0
            continue
        left_weight = 2.0 * intervals[index] + intervals[index - 1]
        right_weight = intervals[index] + 2.0 * intervals[index - 1]
        slopes[index] = (left_weight + right_weight) / (
            left_weight / left + right_weight / right
        )

    def endpoint_slope(
        here: float, neighbor: float, first: float, second: float
    ) -> float:
        """Return a one-sided PCHIP slope clipped to the adjacent secants."""
        value = ((2.0 * here + neighbor) * first - here * second) / (here + neighbor)
        if value * first <= 0.0:
            return 0.0
        if first * second < 0.0 and abs(value) > 3.0 * abs(first):
            return 3.0 * first
        return value

    slopes[0] = endpoint_slope(intervals[0], intervals[1], secants[0], secants[1])
    slopes[-1] = endpoint_slope(
        intervals[-1],
        intervals[-2],
        secants[-1],
        secants[-2],
    )
    return slopes


def _cubic_path(points: np.ndarray) -> str:
    """Build a deterministic shape-preserving cubic SVG path through all knots."""
    if len(points) < 3:
        return _polyline_path(points)
    slopes = _pchip_slopes(points)
    commands = [f"M{_fmt(points[0, 0])} {_fmt(points[0, 1])}"]
    for index in range(len(points) - 1):
        current = points[index]
        following = points[index + 1]
        interval = float(following[0] - current[0])
        control_1 = np.asarray(
            [current[0] + interval / 3.0, current[1] + slopes[index] * interval / 3.0]
        )
        control_2 = np.asarray(
            [
                following[0] - interval / 3.0,
                following[1] - slopes[index + 1] * interval / 3.0,
            ]
        )
        commands.append(
            "C"
            f"{_fmt(control_1[0])} {_fmt(control_1[1])} "
            f"{_fmt(control_2[0])} {_fmt(control_2[1])} "
            f"{_fmt(following[0])} {_fmt(following[1])}"
        )
    return " ".join(commands)


def _unit_vector(vector: np.ndarray) -> np.ndarray:
    """Return a stable unit vector, or a zero vector for a degenerate input."""
    length = float(np.linalg.norm(vector))
    if length <= 1e-12:
        return np.zeros(2, dtype=np.float64)
    return vector.astype(np.float64) / length


def _bezier_point(segment: np.ndarray, parameter: float) -> np.ndarray:
    """Evaluate a cubic Bezier segment at one parameter value."""
    inverse = 1.0 - parameter
    return (
        inverse**3 * segment[0]
        + 3.0 * inverse * inverse * parameter * segment[1]
        + 3.0 * inverse * parameter * parameter * segment[2]
        + parameter**3 * segment[3]
    )


def _bezier_derivatives(
    segment: np.ndarray,
    parameter: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate the first and second derivatives of a cubic Bezier segment."""
    inverse = 1.0 - parameter
    first = 3.0 * (
        inverse * inverse * (segment[1] - segment[0])
        + 2.0 * inverse * parameter * (segment[2] - segment[1])
        + parameter * parameter * (segment[3] - segment[2])
    )
    second = 6.0 * (
        inverse * (segment[2] - 2.0 * segment[1] + segment[0])
        + parameter * (segment[3] - 2.0 * segment[2] + segment[1])
    )
    return first, second


def _chord_parameters(points: np.ndarray) -> np.ndarray:
    """Parameterize ordered points by normalized cumulative chord length."""
    distances = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.concatenate([[0.0], np.cumsum(distances)])
    if cumulative[-1] <= 1e-12:
        return np.linspace(0.0, 1.0, len(points), dtype=np.float64)
    return cumulative / cumulative[-1]


def _generate_bezier_segment(
    points: np.ndarray,
    parameters: np.ndarray,
    left_tangent: np.ndarray,
    right_tangent: np.ndarray,
) -> np.ndarray:
    """Fit one cubic Bezier segment with fixed endpoint tangent directions."""
    first = points[0].astype(np.float64)
    last = points[-1].astype(np.float64)
    c00 = c01 = c11 = x0 = x1 = 0.0
    for point, parameter in zip(points, parameters):
        inverse = 1.0 - float(parameter)
        basis_0 = inverse**3
        basis_1 = 3.0 * float(parameter) * inverse * inverse
        basis_2 = 3.0 * float(parameter) * float(parameter) * inverse
        basis_3 = float(parameter) ** 3
        tangent_0 = left_tangent * basis_1
        tangent_1 = right_tangent * basis_2
        residual = point - (first * (basis_0 + basis_1) + last * (basis_2 + basis_3))
        c00 += float(np.dot(tangent_0, tangent_0))
        c01 += float(np.dot(tangent_0, tangent_1))
        c11 += float(np.dot(tangent_1, tangent_1))
        x0 += float(np.dot(tangent_0, residual))
        x1 += float(np.dot(tangent_1, residual))

    determinant = c00 * c11 - c01 * c01
    if abs(determinant) > 1e-12:
        alpha_left = (x0 * c11 - x1 * c01) / determinant
        alpha_right = (c00 * x1 - c01 * x0) / determinant
    else:
        alpha_left = alpha_right = 0.0

    chord = float(np.linalg.norm(last - first))
    minimum_alpha = max(1e-6, chord * 1e-6)
    if alpha_left < minimum_alpha or alpha_right < minimum_alpha:
        alpha_left = alpha_right = chord / 3.0

    # The traced object is a function y(x), so every fitted segment must also
    # advance monotonically in x.  An unconstrained least-squares fit can make
    # either handle longer than the segment's horizontal span, which reverses
    # the Bezier in x and creates a visible loop even though the trace itself is
    # sound.  Keep both handle directions, but cap their horizontal reach to a
    # third of the segment.  The recursive fitter will introduce extra segments
    # whenever the shorter handles no longer meet the requested error bound.
    horizontal_span = float(last[0] - first[0])
    if horizontal_span > 1e-9:
        if left_tangent[0] > 1e-9:
            alpha_left = min(alpha_left, horizontal_span / (3.0 * left_tangent[0]))
        if right_tangent[0] < -1e-9:
            alpha_right = min(alpha_right, horizontal_span / (-3.0 * right_tangent[0]))

    return np.asarray(
        [
            first,
            first + left_tangent * alpha_left,
            last + right_tangent * alpha_right,
            last,
        ],
        dtype=np.float64,
    )


def _maximum_bezier_error(
    points: np.ndarray,
    segment: np.ndarray,
    parameters: np.ndarray,
) -> tuple[float, int]:
    """Return maximum squared fitting error and its interior split index."""
    split = max(1, len(points) // 2)
    maximum = 0.0
    for index in range(1, len(points) - 1):
        difference = _bezier_point(segment, float(parameters[index])) - points[index]
        squared_error = float(np.dot(difference, difference))
        if squared_error > maximum:
            maximum = squared_error
            split = index
    return maximum, split


def _reparameterize_bezier(
    points: np.ndarray,
    segment: np.ndarray,
    parameters: np.ndarray,
) -> np.ndarray:
    """Improve fit parameters with one Newton-Raphson projection step."""
    improved = parameters.astype(np.float64).copy()
    for index, (point, parameter) in enumerate(zip(points, parameters)):
        curve_point = _bezier_point(segment, float(parameter))
        first, second = _bezier_derivatives(segment, float(parameter))
        difference = curve_point - point
        denominator = float(np.dot(first, first) + np.dot(difference, second))
        if abs(denominator) <= 1e-12:
            continue
        numerator = float(np.dot(difference, first))
        improved[index] = float(np.clip(parameter - numerator / denominator, 0.0, 1.0))
    improved[0] = 0.0
    improved[-1] = 1.0
    return improved


def _fit_bezier_recursive(
    points: np.ndarray,
    left_tangent: np.ndarray,
    right_tangent: np.ndarray,
    maximum_squared_error: float,
    *,
    depth: int = 0,
) -> list[np.ndarray]:
    """Adaptively fit C1-continuous cubic Bezier segments to ordered points."""
    if len(points) == 2:
        distance = float(np.linalg.norm(points[1] - points[0])) / 3.0
        return [
            np.asarray(
                [
                    points[0],
                    points[0] + left_tangent * distance,
                    points[1] + right_tangent * distance,
                    points[1],
                ],
                dtype=np.float64,
            )
        ]

    parameters = _chord_parameters(points)
    segment = _generate_bezier_segment(points, parameters, left_tangent, right_tangent)
    maximum_error, split = _maximum_bezier_error(points, segment, parameters)
    if maximum_error <= maximum_squared_error:
        return [segment]

    if maximum_error <= maximum_squared_error * 4.0:
        for _ in range(5):
            improved = _reparameterize_bezier(points, segment, parameters)
            if np.any(np.diff(improved) <= 0.0):
                break
            parameters = improved
            segment = _generate_bezier_segment(
                points,
                parameters,
                left_tangent,
                right_tangent,
            )
            maximum_error, split = _maximum_bezier_error(points, segment, parameters)
            if maximum_error <= maximum_squared_error:
                return [segment]

    if depth >= 64 or split <= 0 or split >= len(points) - 1:
        split = len(points) // 2
    center_tangent = _unit_vector(points[split - 1] - points[split + 1])
    if not np.any(center_tangent):
        center_tangent = _unit_vector(points[split - 1] - points[split])
    left_segments = _fit_bezier_recursive(
        points[: split + 1],
        left_tangent,
        center_tangent,
        maximum_squared_error,
        depth=depth + 1,
    )
    right_segments = _fit_bezier_recursive(
        points[split:],
        -center_tangent,
        right_tangent,
        maximum_squared_error,
        depth=depth + 1,
    )
    return left_segments + right_segments


def _bezier_path(points: np.ndarray, maximum_error: float) -> tuple[str, int]:
    """Fit and serialize an adaptive sequence of smooth cubic Bezier segments."""
    if len(points) < 3:
        return _polyline_path(points), max(1, len(points) - 1)
    keep = np.concatenate(
        [[True], np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-9]
    )
    fitting_points = points[keep].astype(np.float64)
    left_tangent = _unit_vector(fitting_points[1] - fitting_points[0])
    right_tangent = _unit_vector(fitting_points[-2] - fitting_points[-1])
    segments = _fit_bezier_recursive(
        fitting_points,
        left_tangent,
        right_tangent,
        max(0.05, float(maximum_error)) ** 2,
    )
    commands = [f"M{_fmt(segments[0][0, 0])} {_fmt(segments[0][0, 1])}"]
    for segment in segments:
        commands.append(
            "C"
            f"{_fmt(segment[1, 0])} {_fmt(segment[1, 1])} "
            f"{_fmt(segment[2, 0])} {_fmt(segment[2, 1])} "
            f"{_fmt(segment[3, 0])} {_fmt(segment[3, 1])}"
        )
    return " ".join(commands), len(segments)


def _bezier_path_with_fixed_tangent(
    points: np.ndarray,
    anchor: np.ndarray,
    forward_tangent: np.ndarray,
    maximum_error: float,
) -> tuple[str, int]:
    """Fit both curve branches with an exact shared tangent at ``anchor``."""
    fitting_points = points[
        np.concatenate([[True], np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-9])
    ].astype(np.float64)
    anchor = anchor.astype(np.float64)
    direction = _unit_vector(forward_tangent)
    if len(fitting_points) < 3 or not np.any(direction):
        return _bezier_path(fitting_points, maximum_error)

    left = fitting_points[fitting_points[:, 0] < anchor[0] - 1e-7]
    right = fitting_points[fitting_points[:, 0] > anchor[0] + 1e-7]
    if len(left) < 1 or len(right) < 1:
        return _bezier_path(fitting_points, maximum_error)
    left = np.vstack([left, anchor])
    right = np.vstack([anchor, right])
    threshold = max(0.05, float(maximum_error)) ** 2
    left_segments = _fit_bezier_recursive(
        left,
        _unit_vector(left[1] - left[0]),
        -direction,
        threshold,
    )
    right_segments = _fit_bezier_recursive(
        right,
        direction,
        _unit_vector(right[-2] - right[-1]),
        threshold,
    )
    segments = left_segments + right_segments
    commands = [f"M{_fmt(segments[0][0, 0])} {_fmt(segments[0][0, 1])}"]
    for segment in segments:
        commands.append(
            "C"
            f"{_fmt(segment[1, 0])} {_fmt(segment[1, 1])} "
            f"{_fmt(segment[2, 0])} {_fmt(segment[2, 1])} "
            f"{_fmt(segment[3, 0])} {_fmt(segment[3, 1])}"
        )
    return " ".join(commands), len(segments)
