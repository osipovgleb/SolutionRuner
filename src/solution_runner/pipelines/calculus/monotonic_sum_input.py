"""Recover derivative signs and integer abscissas from SVG or cleaned rasters."""

import hashlib
import json
import math
import re
from copy import deepcopy
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import pairwise
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from bs4 import BeautifulSoup

from ..equations.linear_system_intervals import Interval
from ..probability.common import UnsupportedCondition, normalize
from . import (
    curve_levels,
    derivative_level_geometry,
    derivative_level_input,
    derivative_level_render,
    graph_extrema,
    graph_input,
    graph_monotonic,
    graph_monotonic_chart,
    graph_stationary,
    primitive_curves,
    primitive_svg,
    raster_primitive,
    tangent_native,
)
from .common import answer

CACHE = Path(__file__).with_name("assets") / "monotonic-sum-curves.json"


@dataclass
class Graph:
    question: object
    condition: dict
    asset: dict
    source: bytes
    model: dict | None
    entry: dict
    zeros: tuple
    bands: tuple
    integers: tuple
    marks: tuple = ()
    longest: Interval | None = None

    @property
    def result(self):
        if self.longest is not None:
            return answer(self.longest.upper - self.longest.lower)
        if self.question.operation == "stationary" or (
            self.question.operation == "count" and self.question.derivative
        ):
            return str(len(self.marks))
        return str(
            len(self.integers)
            if self.question.operation == "count"
            else sum(self.integers)
        )


def read(context):
    clean = deepcopy(context)
    content = clean["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    if len(condition.get("asset_keys", [])) != 1:
        raise UnsupportedCondition("one derivative graph is required")
    asset = next(
        a for a in content["assets"] if a["asset_key"] == condition["asset_keys"][0]
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) != 1 or images[0].get("data-asset-id") != asset["asset_id"]:
        raise UnsupportedCondition("the visible graph must match its source asset")
    images[0].decompose()
    condition["html"], condition["asset_keys"], content["assets"] = str(soup), [], []
    text = normalize(graph_input._read_text(clean)[4]).replace("\u2060", "")
    text = re.sub(r"(на интервале)\((-?\d+),(-?\d+)\)", r"\1(\2;\3)", text)
    try:
        question = graph_monotonic.parse(text)
    except UnsupportedCondition:
        try:
            question = graph_extrema.parse(text)
        except UnsupportedCondition:
            stationary_question = graph_stationary.parse(text)
            if stationary_question.kind != "count":
                raise UnsupportedCondition("a stationary-point count is required")
            question = graph_monotonic.Question(
                stationary_question.domain,
                False,
                False,
                "stationary",
                span=stationary_question.interval
                if stationary_question.interval != stationary_question.domain
                else None,
            )
    if not (
        (
            question.operation == "global"
            and question.derivative
            and not question.comparisons
        )
        or (question.operation in ("sum", "length") and question.derivative)
        or (
            question.operation in ("count", "point")
            and question.derivative
            and question.domain is not None
            and question.target in ("max", "min", "extrema")
        )
        or (
            question.operation == "sum"
            and not question.derivative
            and getattr(question, "target", None) == "extrema"
        )
        or (
            question.operation in ("count", "stationary", "value")
            and not question.derivative
        )
    ):
        raise UnsupportedCondition(
            "a sum of integers in derivative sign intervals is required"
        )
    original = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    return question, original, asset


def ordinate(entry, x):
    """Evaluate a cubic at one SVG abscissa, keeping its exact native geometry."""
    for segment in np.asarray(entry["curve_segments"]):
        if segment[0, 0] > segment[-1, 0]:
            segment = segment[::-1]
        if segment[0, 0] - 1e-5 <= x <= segment[-1, 0] + 1e-5:
            lo, hi = 0.0, 1.0
            for _ in range(45):
                t = (lo + hi) / 2
                point = (
                    (1 - t) ** 3 * segment[0]
                    + 3 * (1 - t) ** 2 * t * segment[1]
                    + 3 * (1 - t) * t * t * segment[2]
                    + t**3 * segment[3]
                )
                if point[0] < x:
                    lo = t
                else:
                    hi = t
            return float(point[1])
    raise UnsupportedCondition("the source curve does not cover the requested abscissa")


def recover(data, q):
    trace = graph_stationary.Question(
        "count", q.domain, q.domain, horizontal=Fraction(0)
    )
    if raster_primitive.META.encode() in data:
        return raster_primitive.embedded(
            data.replace("y = f′(x)".encode(), b"y = F(x)").replace(
                b"y = f(x)", b"y = F(x)"
            ),
            trace,
        )
    digest = hashlib.sha256(data).hexdigest()
    cached = json.loads(CACHE.read_text()).get(digest) if CACHE.exists() else None
    if cached is None:
        return deepcopy(derivative_level_input._recover(data, trace))
    if cached["source_sha256"] != digest or list(map(Fraction, cached["domain"])) != [
        q.domain.lower,
        q.domain.upper,
    ]:
        raise UnsupportedCondition(
            "the cached curve belongs to another source or domain"
        )
    primitive_curves.verify(cached)
    return deepcopy(cached)


def native(data, q):
    """Read source SVG cubic paths without rebuilding the drawing."""
    from solution_runner.converters.graph_png_to_svg_by_contrast import fit_grid_axis

    try:
        root = ET.fromstring(tangent_native.presentation(data))
    except (ET.ParseError, UnicodeError) as error:
        raise UnsupportedCondition(
            "the downloaded diagram is not a supported SVG or raster"
        ) from error
    lines = tangent_native.straight_segments(root)
    black = [
        p
        for node, p in lines
        if node.get("stroke", "").lower() in ("black", "#000000", "#000")
    ]
    horizontal = [p for p in black if abs(p[3] - p[1]) < 0.3 and abs(p[2] - p[0]) > 30]
    vertical = [p for p in black if abs(p[2] - p[0]) < 0.3 and abs(p[3] - p[1]) > 30]
    if not horizontal or not vertical:
        raise UnsupportedCondition("native derivative axes are required")
    ox = max(vertical, key=lambda p: abs(p[3] - p[1]))[0]
    oy = max(horizontal, key=lambda p: abs(p[2] - p[0]))[1]
    gray = [
        p
        for node, p in lines
        if node.get("stroke", "").lower() in ("#adaaaa", "#c0bfbf")
    ]
    xs = sorted({p[0] for p in gray if abs(p[2] - p[0]) < 0.01})
    ys = sorted({p[1] for p in gray if abs(p[3] - p[1]) < 0.01})
    if min(len(xs), len(ys)) < 4:
        raise UnsupportedCondition("the native derivative grid is unresolved")
    ux = fit_grid_axis(xs, max(xs) - min(xs) + 1).step
    uy = fit_grid_axis(ys, max(ys) - min(ys) + 1).step
    segments = []
    for node in root.iter(tangent_native.NS + "path"):
        if node.get("stroke", "").lower() == "#143b8f":
            if node.get("transform"):
                raise UnsupportedCondition(
                    "the source curve has a local coordinate transform"
                )
            segments.extend(primitive_svg._segments(node.get("d", "")))
    segments = sorted(
        (s if s[-1, 0] > s[0, 0] else s[::-1] for s in segments), key=lambda s: s[0, 0]
    )
    if not segments:
        raise UnsupportedCondition("one native derivative curve is required")
    if q.domain is None:
        # Only the connected part covering the question's segment is needed.
        components = []
        for segment in segments:
            if not components or segment[0, 0] - components[-1][-1][-1, 0] > 0.05 * ux:
                components.append([])
            components[-1].append(segment)
        lower, upper = (ox + float(x) * ux for x in (q.span.lower, q.span.upper))
        covered = [
            part
            for part in components
            if part[0][0, 0] < lower < upper < part[-1][-1, 0]
        ]
        if len(covered) != 1:
            raise UnsupportedCondition(
                "one connected graph must cover the requested segment"
            )
        segments = covered[0]
    domain = ((segments[0][0, 0] - ox) / ux, (segments[-1][-1, 0] - ox) / ux)
    if q.domain is not None and (
        max(abs(float(a) - b) for a, b in zip((q.domain.lower, q.domain.upper), domain))
        > 0.15
    ):
        raise UnsupportedCondition(
            "the native curve endpoints disagree with the stated domain"
        )
    return {
        "svg_origin": [ox, oy],
        "svg_unit": uy,
        "x_unit": ux,
        "curve_segments": [s.tolist() for s in segments],
    }


def render_model(model, question):
    svg = derivative_level_render._render(model)
    return svg if question.derivative else svg.replace("y = f′(x)", "y = f(x)")


def stationary(entry):
    """Reuse the native cubic stationary-point detector, including flat inflections."""
    segments = sorted(
        (np.asarray(s) for s in entry["curve_segments"]), key=lambda s: s[0, 0]
    )
    start, end = segments[0][0, 0], segments[-1][-1, 0]
    ox = entry["svg_origin"][0]
    unit = entry.get("x_unit", entry["svg_unit"])
    candidates = primitive_svg._stationary_candidates(segments, (start, end, ox, unit))
    # Some native exports join two arcs with rounded, nonhorizontal handles.
    # A reversal at that join is still an extremum even when dy/dt has no
    # zero inside either cubic. Keep the source position and shape unchanged.
    for left, right in pairwise(segments):
        if np.linalg.norm(left[-1] - right[0]) > 0.05 * unit:
            raise UnsupportedCondition("the source curve has disconnected arcs")
        before = left[-1, 1] - primitive_svg._at(left, 0.999)[1]
        after = primitive_svg._at(right, 0.001)[1] - right[0, 1]
        if before * after < 0:
            candidates.append({"svg": left[-1].tolist()})
    return tuple(
        curve_levels.distinct_points([tuple(p["svg"]) for p in candidates], start, end)
    )


def geometry(data, q):
    model = None
    if (
        data.startswith((raster_primitive.PNG, b"\xff\xd8"))
        or raster_primitive.META.encode() in data
    ):
        if q.domain is None:
            raise UnsupportedCondition("the raster graph requires a stated domain")
        model = recover(data, q)
        source = render_model(model, q).encode()
        entry = derivative_level_geometry._model_entry(model)
        knots = np.asarray(model["knots"])
        ox = -math.floor(min(float(model["domain"][0]) - 1, -2)) * 20
        oy = math.ceil(max(knots[:, 1].max() + 1, 2)) * 20
        entry["svg_origin"] = [ox, oy]
        entry["curve_segments"] = (
            np.asarray(entry["curve_segments"]) + [ox, oy]
        ).tolist()
        for node in entry["curve_nodes"]:
            node["svg"] = (np.asarray(node["svg"]) + [ox, oy]).tolist()
    else:
        source = data
        entry = native(data, q)
    return source, entry, model


def input(context, data):
    q, condition, asset = read(context)
    if not isinstance(data, bytes):
        raise UnsupportedCondition("current derivative graph bytes are required")
    if q.operation == "stationary" and asset["asset_id"] in graph_input.EVIDENCE:
        from ..probability.condition_diagram import verify_download

        parsed, _, points = graph_stationary._input(context)
        verify_download(parsed[6], data)
        return Graph(
            q,
            condition,
            asset,
            data,
            None,
            parsed[5],
            (),
            (),
            (),
            tuple(p["svg"] for p in points),
        )
    if q.operation in ("count", "point") and q.derivative:
        audited_role = graph_input.EVIDENCE.get(asset["asset_id"], {}).get("curve_name")
        if audited_role is not None and audited_role != "derivative":
            raise UnsupportedCondition("the audited graph role must match the question")
    source, entry, model = geometry(data, q)
    zeros = tuple(
        curve_levels.distinct_points(
            curve_levels.svg_intersections(entry, 0),
            min(s[0][0] for s in entry["curve_segments"]),
            max(s[-1][0] for s in entry["curve_segments"]),
        )
    )
    if not q.derivative:
        zeros = stationary(entry)
    if q.operation == "stationary":
        if q.span is not None:
            if q.span.lower <= q.domain.lower or q.span.upper >= q.domain.upper:
                raise UnsupportedCondition(
                    "the section must lie inside the open graph domain"
                )
            ox = entry["svg_origin"][0]
            unit = entry.get("x_unit", entry["svg_unit"])
            points = []
            for x, y in zeros:
                value = (x - ox) / unit
                if abs(value - round(value)) <= 0.10:
                    value = round(value)
                points.append({"x": str(value), "kind": "stationary", "svg": (x, y)})
            zeros = tuple(p["svg"] for p in graph_stationary.select(points, q.span))
        return Graph(q, condition, asset, source, model, entry, (), (), (), zeros)
    ox, oy = entry["svg_origin"]
    unit = entry.get("x_unit", entry["svg_unit"])
    if q.domain is None:
        bounds = [entry["curve_segments"][0][0][0], entry["curve_segments"][-1][-1][0]]
        q = replace(
            q, domain=Interval(*(Fraction(str((x - ox) / unit)) for x in bounds))
        )
    left, right = ox + float(q.domain.lower) * unit, ox + float(q.domain.upper) * unit
    cuts = [left, *(x for x, _ in zeros), right]
    bands = tuple(
        (
            a,
            b,
            (1 if ordinate(entry, (a + b) / 2) < oy else -1)
            if q.derivative
            else (
                1
                if ordinate(entry, a + 0.25 * (b - a))
                > ordinate(entry, a + 0.75 * (b - a))
                else -1
            ),
        )
        for a, b in pairwise(cuts)
    )
    if q.operation in ("count", "point") and q.derivative:
        span = q.interval
        if (
            span.lower < q.domain.lower
            or span.upper > q.domain.upper
            or span.lower == q.domain.lower
            and span.lower_closed
            or span.upper == q.domain.upper
            and span.upper_closed
        ):
            raise UnsupportedCondition(
                "the selection interval lies outside the open function domain"
            )
        marks = []
        abscissae = []
        for index, point in enumerate(zeros):
            before, after = bands[index][2], bands[index + 1][2]
            if before == after or q.target not in (
                "extrema",
                "max" if before > 0 else "min",
            ):
                continue
            x = (point[0] - ox) / unit
            if abs(x - round(x)) <= 0.10:
                x = round(x)
            if (span.lower < x or span.lower_closed and span.lower == x) and (
                x < span.upper or span.upper_closed and x == span.upper
            ):
                marks.append(point)
                abscissae.append(x)
        if q.operation == "point":
            if len(abscissae) != 1 or not isinstance(abscissae[0], int):
                raise UnsupportedCondition(
                    "the requested extremum must have a unique exact abscissa"
                )
            return Graph(
                q,
                condition,
                asset,
                source,
                model,
                entry,
                zeros,
                bands,
                tuple(abscissae),
            )
        return Graph(
            q, condition, asset, source, model, entry, zeros, bands, (), tuple(marks)
        )
    if q.operation in ("global", "length"):
        nodes = [{"x": q.domain.lower}]
        for x, _ in zeros:
            value = (x - ox) / unit
            nearest = round(value)
            if abs(value - nearest) <= 0.10:
                nodes.append({"x": nearest})
            else:
                nodes.append(
                    {
                        "x_bounds": (math.floor(value), math.ceil(value)),
                        "x_bounds_open": (True, True),
                    }
                )
        nodes.append({"x": q.domain.upper})
        chart = []
        for index, (a, b, band) in enumerate(
            zip(nodes[:-1], nodes[1:], bands, strict=True)
        ):
            left_closed = index > 0 or q.domain.lower_closed
            right_closed = index < len(bands) - 1 or q.domain.upper_closed
            if chart and chart[-1][4] == band[2]:
                a, _, left_closed, _, _ = chart.pop()
            chart.append((a, b, left_closed, right_closed, band[2]))
        if q.operation == "length":
            _, (a, b, lc, rc, _) = graph_monotonic_chart.longest_band(
                [band for band in chart if band[4] == q.sign]
            )
            return Graph(
                q,
                condition,
                asset,
                source,
                model,
                entry,
                zeros,
                bands,
                (),
                longest=Interval(Fraction(a["x"]), Fraction(b["x"]), lc, rc),
            )
        result = graph_monotonic_chart.global_point(q, chart)
        if result.denominator != 1:
            raise UnsupportedCondition("an exact integer extremum abscissa is required")
        lower, upper = ox + float(q.span.lower) * unit, ox + float(q.span.upper) * unit
        visible = tuple(
            (max(a, lower), min(b, upper), sign)
            for a, b, sign in bands
            if min(b, upper) - max(a, lower) > 0.10 * unit
        )
        selected_zeros = tuple(
            p
            for p, node in zip(zeros, nodes[1:-1], strict=True)
            if graph_monotonic_chart.compare(node, q.span.lower) > 0
            and graph_monotonic_chart.compare(node, q.span.upper) < 0
        )
        return Graph(
            q,
            condition,
            asset,
            source,
            model,
            entry,
            selected_zeros,
            visible,
            (int(result),),
        )
    # Grid-coincident roots have at most a fraction of a stroke of export error.
    # Never move the curve: normalize only the integer interval-membership test.
    if getattr(q, "target", "") == "neighborhood":
        merged = []
        for a, b, sign in bands:
            if merged and merged[-1][2] == sign:
                a = merged.pop()[0]
            merged.append((a, b, sign))
        bands = tuple(merged)
        cuts = [bands[0][0], *(b for _, b, _ in bands)]
    exact_cuts = []
    for x in cuts:
        value = (x - ox) / unit
        if abs(value - round(value)) <= 0.10:
            value = float(round(value))
        exact_cuts.append(value)
    values = tuple(
        n
        for n in range(
            math.floor(float(q.domain.lower)) + 1, math.ceil(float(q.domain.upper))
        )
        if any(
            (a <= n <= b if q.derivative else a < n < b)
            and band[2] == getattr(q, "sign", None)
            for a, b, band in zip(exact_cuts, exact_cuts[1:], bands)
        )
    )
    if q.operation == "sum" and not q.derivative:
        values = []
        for i, (x, _) in enumerate(zeros):
            if bands[i][2] == bands[i + 1][2]:
                continue  # A horizontal inflection is not an extremum.
            value = (x - ox) / unit
            if abs(value - round(value)) > 0.10:
                raise UnsupportedCondition("an extremum abscissa is not grid-readable")
            values.append(round(value))
        if len(set(values)) != len(values):
            raise UnsupportedCondition("distinct extrema have unresolved abscissas")
        values = tuple(values)
    if not values:
        raise UnsupportedCondition(
            "no integer abscissas were established in the requested intervals"
        )
    return Graph(q, condition, asset, source, model, entry, zeros, bands, values)
