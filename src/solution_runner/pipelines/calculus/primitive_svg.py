"""Read stationary points directly from untransformed native cubic SVG curves."""

import re
from itertools import pairwise
from xml.etree import ElementTree as ET

import numpy as np

from ..probability.common import UnsupportedCondition
from . import graph_stationary

_TOKEN = re.compile(r"[MmCcSsLl]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")


def _segments(data):
    tokens = _TOKEN.findall(data)
    if re.sub(r"[\s,]", "", _TOKEN.sub("", data)):
        raise UnsupportedCondition(
            "the native graph uses unsupported SVG path commands"
        )
    current = np.zeros(2)
    previous = None
    segments = []
    command = None
    i = 0
    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1
        if command is None:
            raise UnsupportedCondition("invalid native SVG path")
        count = {"m": 2, "c": 6, "s": 4, "l": 2}[command.lower()]
        if i + count > len(tokens) or any(t.isalpha() for t in tokens[i : i + count]):
            raise UnsupportedCondition("incomplete native SVG segment")
        values = np.array(list(map(float, tokens[i : i + count]))).reshape(-1, 2)
        i += count
        if command.islower():
            values += current
        if command.lower() == "m":
            current = values[0]
            previous = None
            command = "l" if command.islower() else "L"
            continue
        if command.lower() == "l":
            end = values[0]
            controls = np.array(
                [
                    current,
                    current + (end - current) / 3,
                    current + 2 * (end - current) / 3,
                    end,
                ]
            )
            previous = None
        elif command.lower() == "s":
            first = 2 * current - previous if previous is not None else current
            controls = np.array([current, first, *values])
            previous = values[-2]
        else:
            controls = np.array([current, *values])
            previous = values[-2]
        current = controls[-1]
        segments.append(controls)
    return segments


def _at(segment, t):
    return (
        np.array([(1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t**3])
        @ segment
    )


def _stationary_candidates(segments, frame):
    start, end, origin, unit = frame
    candidates = []
    for index, segment in enumerate(segments):
        p0, p1, p2, p3 = segment
        # A backwards fold is not a graph of a function.
        derivative_x = [
            3 * (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]),
            6 * (p0[0] - 2 * p1[0] + p2[0]),
            3 * (p1[0] - p0[0]),
        ]
        ts = [0.0, 1.0]
        if abs(derivative_x[0]) > 1e-12:
            ts.append(float(np.clip(-derivative_x[1] / (2 * derivative_x[0]), 0, 1)))
        if min(np.polyval(derivative_x, ts)) < -max(0.5, unit * 0.05):
            raise UnsupportedCondition("the native curve folds backwards")
        a, b, c = (
            3 * (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]),
            6 * (p0[1] - 2 * p1[1] + p2[1]),
            3 * (p1[1] - p0[1]),
        )
        coefficients = np.trim_zeros([a, b, c], "f")
        if not len(coefficients):
            raise UnsupportedCondition(
                "a horizontal curve segment has infinitely many stationary points"
            )
        for t in np.roots(coefficients):
            if abs(t.imag) > 1e-7 or not -1e-7 <= t.real <= 1 + 1e-7:
                continue
            t = float(np.clip(t.real, 0, 1))
            p = _at(segment, t)
            if p[0] <= start + unit * 0.001 or p[0] >= end - unit * 0.001:
                continue

            def dy(curve, value):
                return 3 * (
                    (1 - value) ** 2 * (curve[1, 1] - curve[0, 1])
                    + 2 * (1 - value) * value * (curve[2, 1] - curve[1, 1])
                    + value**2 * (curve[3, 1] - curve[2, 1])
                )

            before = dy(segment, max(0, t - 0.001))
            after = dy(segment, min(1, t + 0.001))
            if t < 0.001 and index:
                before = dy(segments[index - 1], 0.999)
            if t > 0.999 and index + 1 < len(segments):
                after = dy(segments[index + 1], 0.001)
            kind = (
                "max"
                if before < 0 and after > 0
                else "min"
                if before > 0 and after < 0
                else "stationary"
            )
            # A horizontal handle on only one side of an SVG join is not a
            # stationary point of the drawn function. Illustrator paths can
            # contain such joins just beside the actual extremum.
            if kind == "stationary":
                if t < 1e-7 and index and abs(dy(segments[index - 1], 1)) > unit * 1e-6:
                    continue
                if (
                    t > 1 - 1e-7
                    and index + 1 < len(segments)
                    and abs(dy(segments[index + 1], 0)) > unit * 1e-6
                ):
                    continue
            candidates.append(
                {"x": str((p[0] - origin) / unit), "kind": kind, "svg": p.tolist()}
            )
    return candidates


def read(data, question):
    if question.kind not in ("primitive", "count"):
        raise UnsupportedCondition(
            "this native SVG question is not a zero-count problem"
        )
    root = ET.fromstring(data)
    if any(n.get("transform") for n in root.iter()):
        raise UnsupportedCondition(
            "transformed native graph paths need separate review"
        )
    segments = []
    for node in root.iter():
        if node.tag.endswith("path") and node.get("stroke", "").lower() == "#143b8f":
            segments.extend(_segments(node.get("d", "")))
    segments = [
        s if s[-1, 0] > s[0, 0] else s[::-1]
        for s in segments
        if abs(s[-1, 0] - s[0, 0]) > 1e-6
    ]
    segments.sort(key=lambda s: s[0, 0])
    if not segments:
        raise UnsupportedCondition("one native cubic graph is required")
    if any(np.linalg.norm(a[-1] - b[0]) > 1.5 for a, b in pairwise(segments)):
        raise UnsupportedCondition("the native graph has disconnected branches")
    start, end = segments[0][0, 0], segments[-1][-1, 0]
    unit = (end - start) / float(question.domain.upper - question.domain.lower)
    origin = start - float(question.domain.lower) * unit
    if unit <= 0:
        raise UnsupportedCondition("invalid native graph coordinate frame")
    candidates = _stationary_candidates(segments, (start, end, origin, unit))
    candidates.sort(key=lambda p: float(p["x"]))
    points = []
    for p in candidates:
        if points and np.linalg.norm(np.array(p["svg"]) - points[-1]["svg"]) <= min(
            1.0, unit * 0.05
        ):
            # Rounded control points can add a microscopic turn at a join.
            # Keep the actual extremum rather than count its handle twice.
            if points[-1]["kind"] == "stationary" and p["kind"] != "stationary":
                points[-1] = p
            continue
        points.append(p)
    selected = graph_stationary.select(points, question.interval)
    return {
        "svg_origin": [origin, 0],
        "svg_unit": unit,
        "svg_bracket_y": [10, float(root.get("viewBox").split()[3]) - 10],
    }, selected
