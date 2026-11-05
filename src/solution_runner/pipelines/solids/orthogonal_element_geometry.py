"""Bind named vertices to marked lengths without assuming unmarked offsets."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from .orthogonal_geometry import OrthogonalSolid
from .orthogonal_shapes import block, step_rise
from .regular_prism_geometry import cosine, degrees

VERTEX = r"[A-G](?:_[123])?"
POINT = rf"(?:{VERTEX}|K)"


def rectangle(x0, x1, y0, y1, z, names):
    return {
        name: sp.ImmutableMatrix(p)
        for name, p in zip(
            names,
            ((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)),
            strict=True,
        )
    }


def step_points(g):
    x, y, h, rise, w = (
        g[k] for k in ("width", "depth", "height", "rise", "upper_width")
    )
    points = rectangle(0, x, 0, y, 0, ("A", "B", "C", "D"))
    points.update(rectangle(0, w, 0, y, h, ("A_2", "B_2", "C_2", "D_2")))
    points.update(rectangle(w, x, 0, y, h - rise, ("A_1", "B_1", "C_1", "D_1")))
    return points


def ridge_points(g):
    x, y, low, rise, w, right = (
        g[k]
        for k in ("width", "depth", "base_height", "rise", "upper_width", "right_ledge")
    )
    left = x - w - right
    points = rectangle(0, x, 0, y, 0, ("D", "C", "B", "A"))
    points.update(rectangle(0, x, 0, y, low, ("D_1", "C_1", "B_1", "A_1")))
    points.update(rectangle(left, left + w, 0, y, low, ("D_2", "C_2", "B_2", "A_2")))
    points.update(
        rectangle(left, left + w, 0, y, low + rise, ("D_3", "C_3", "B_3", "A_3"))
    )
    return points


def elbow_points(g):
    x, h, w, d = (g[k] for k in ("width", "height", "upper_width", "upper_depth"))
    points = {
        "F": (0, 0, 0),
        "E": (x, 0, 0),
        "D": (x, -d, 0),
        "C": (w, -d, 0),
        "D_2": (0, 0, h),
        "C_2": (w, 0, h),
        "B_2": (w, -d, h),
        "A_2": (0, -d, h),
    }
    if "depth" in g:
        points.update(A=(0, -g["depth"], 0), B=(w, -g["depth"], 0))
    return {name: sp.ImmutableMatrix(p) for name, p in points.items()}


def step(g):
    solid = step_rise(
        tuple(g[k] for k in ("width", "depth", "height", "rise", "upper_width"))
    ).solid
    points = step_points(g)
    if any(not solid.on_boundary(tuple(p)) for p in points.values()):
        raise ContentPlanError("a step vertex lies outside its actual boundary")
    return points


def ridge(g):
    x, y, low, rise, w, right = (
        g[k]
        for k in ("width", "depth", "base_height", "rise", "upper_width", "right_ledge")
    )
    left = x - w - right
    if left <= 0:
        raise ContentPlanError("the upper ridge must leave both marked shoulders")
    solid = OrthogonalSolid((block((x, y, low)), block((w, y, rise), (left, 0, low))))
    points = ridge_points(g)
    if any(not solid.on_boundary(tuple(p)) for p in points.values()):
        raise ContentPlanError("a ridge vertex lies outside its actual boundary")
    return points


def elbow(g):
    if (
        g["upper_width"] >= g["width"]
        or "depth" in g
        and g["depth"] <= g["upper_depth"]
    ):
        raise ContentPlanError("the elbow arms must extend beyond the tower")
    return elbow_points(g)


def symbolic_points(kind, given):
    frame(kind, given)
    symbols = {k: sp.Symbol(k, positive=True) for k in given}
    return {"step": step_points, "ridge": ridge_points, "elbow": elbow_points}[kind](
        symbols
    )


def frame(kind, given):
    factories = {"step": step, "ridge": ridge, "elbow": elbow}
    if kind not in factories or not isinstance(given, dict):
        raise ContentPlanError(
            "an explicitly reviewed named orthogonal figure is required"
        )
    allowed = {
        "step": {"width", "depth", "height", "rise", "upper_width"},
        "ridge": {
            "width",
            "depth",
            "base_height",
            "rise",
            "upper_width",
            "right_ledge",
        },
        "elbow": {"width", "height", "upper_width", "upper_depth", "depth"},
    }[kind]
    required = allowed - ({"depth"} if kind == "elbow" else set())
    if not required <= set(given) <= allowed:
        raise ContentPlanError(
            "the named figure dimensions are incomplete or unreviewed"
        )
    if any(
        not isinstance(v, str) or re.fullmatch(r"[1-9]\d*(?:/[1-9]\d*)?", v) is None
        for v in given.values()
    ):
        raise ContentPlanError(
            "reviewed positive rational diagram lengths are required"
        )
    return factories[kind]({k: sp.Rational(v) for k, v in given.items()})


def requested(points, raw, count):
    if (
        not isinstance(raw, str)
        or re.fullmatch(rf"(?:{POINT}){{{count}}}", raw) is None
    ):
        raise ContentPlanError("complete canonical named vertices are required")
    names = tuple(re.findall(POINT, raw))
    if len(set(names)) != count or any(n not in points for n in names):
        raise ContentPlanError(
            "the requested vertices need explicit diagram measurements"
        )
    return tuple(points[n] for n in names)


def squared(points, segment):
    a, b = requested(points, segment, 2)
    delta = b - a
    return sp.expand(delta.dot(delta))


def answer(points, mode, raw):
    if mode in {"distance", "distance_squared"}:
        total = squared(points, raw)
        return sp.sqrt(total) if mode == "distance" else total
    if mode not in {"angle", "tangent"}:
        raise ContentPlanError("one reviewed named geometric quantity is required")
    a, b, c = requested(points, raw, 3)
    cos = cosine(a - b, c - b)
    if mode == "angle":
        return degrees(cos)
    if cos <= 0:
        raise ContentPlanError("the parent tangent method requires an acute angle")
    return sp.simplify(sp.sqrt(1 - cos * cos) / cos)
