"""Isolated, read-only constrained fitCurves experiment (upstream MIT in vendor/)."""

import itertools

import numpy as np
from scipy.optimize import minimize

from .curve_fitting import fit_curves as fitCurves

_original_generate = fitCurves.generateBezier


def bounded_generate(points, parameters, left, right):
    curve = np.array(_original_generate(points, parameters, left, right), dtype=float)
    span = curve[3] - curve[0]
    for index, origin in ((1, 0), (2, 3)):
        vector = curve[index] - curve[origin]
        ratio = 1.0
        for axis in (0, 1):
            if abs(vector[axis]) > 1e-12:
                ratio = min(ratio, 0.49 * abs(span[axis]) / abs(vector[axis]))
        curve[index] = curve[origin] + vector * ratio
    return curve





def verify(segments):
    for s in segments:
        if not np.all(np.diff(s[:, 0]) >= -1e-8):
            raise ValueError("curve reverses x")
        sign = np.sign(s[-1, 1] - s[0, 1])
        if not sign or not np.all(np.diff(s[:, 1]) * sign >= -1e-8):
            raise ValueError("extra extremum")
    for a, b in itertools.pairwise(segments):
        if not np.allclose(a[-1], b[0], atol=1e-12):
            raise ValueError("disconnected curve")


def fit(trace, anchors, tolerance=0.14):
    from . import raster_primitive

    trace = raster_primitive.extrema_reader._project_between_extrema(trace, anchors)
    result = []
    for i, (a, b) in enumerate(itertools.pairwise(anchors)):
        points = np.vstack((a, trace[(trace[:, 0] > a[0]) & (trace[:, 0] < b[0])], b))
        left = (
            np.array([1.0, 0.0])
            if i
            else fitCurves.normalize(points[min(3, len(points) - 1)] - a)
        )
        right = (
            np.array([-1.0, 0.0])
            if i < len(anchors) - 2
            else fitCurves.normalize(points[max(0, len(points) - 4)] - b)
        )
        segments = np.array(fitCurves.fitCubic(points, left, right, tolerance**2, generator=bounded_generate))
        verify(segments)
        if not np.array_equal(segments[0, 0], a) or not np.array_equal(
            segments[-1, -1], b
        ):
            raise ValueError("anchor moved")
        result.extend(segments)
    verify(result)
    return np.array(result)


def harmonize(s):
    n = len(s)
    p0 = s[:, 0]
    p3 = s[:, 3]
    v0 = s[:, 1] - p0
    v1 = p3 - s[:, 2]
    l0 = np.linalg.norm(v0, axis=1)
    l1 = np.linalg.norm(v1, axis=1)
    u0 = v0 / l0[:, None]
    u1 = v1 / l1[:, None]
    if np.max(np.linalg.norm(u1[:-1] - u0[1:], axis=1)) > 1e-6:
        raise ValueError("mismatched tangents")
    initial = np.column_stack((l0, l1)).ravel()
    span = np.linalg.norm(p3 - p0, axis=1)
    scales = np.repeat(span, 2)

    def curves(z):
        l = z.reshape(n, 2)
        return np.stack(
            (p0, p0 + u0 * l[:, 0, None], p3 - u1 * l[:, 1, None], p3), axis=1
        )

    def cross(a, b):
        return a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]

    def curvature(z):
        l = z.reshape(n, 2)
        a = (2 / 3) * cross(u0, p3 - p0 - u1 * l[:, 1, None]) / l[:, 0] ** 2
        b = (2 / 3) * cross(u1, p0 - p3 + u0 * l[:, 0, None]) / l[:, 1] ** 2
        return a, b

    start, end = curvature(initial)
    kscale = 1 + np.maximum(abs(end[:-1]), abs(start[1:]))

    def equal(z):
        a, b = curvature(z)
        return (b[:-1] - a[1:]) / kscale

    sign = np.sign(p3[:, 1] - p0[:, 1])

    def monotone(z):
        delta = np.diff(curves(z), axis=1)
        return np.concatenate(
            (delta[:, :, 0].ravel(), (delta[:, :, 1] * sign[:, None]).ravel())
        )

    def objective(z):
        return np.sum(((z - initial) / scales) ** 2)

    upper = []
    for i in range(n):
        for direction in (u0[i], u1[i]):
            upper.append(
                min(
                    abs((p3[i, j] - p0[i, j]) / direction[j])
                    for j in (0, 1)
                    if abs(direction[j]) > 1e-9
                )
                * 0.999
            )
    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=list(zip(np.maximum(scales * 0.03, 1e-6), upper)),
        constraints=[{"type": "eq", "fun": equal}, {"type": "ineq", "fun": monotone}],
        options={"maxiter": 1000, "ftol": 1e-11},
    )
    if (
        not result.success
        or max(abs(equal(result.x))) > 1e-6
        or min(monotone(result.x)) < -1e-8
    ):
        raise ValueError("curvature optimization: " + str(result.message))
    out = curves(result.x)
    verify(out)
    if not np.array_equal(out[:, 0], p0) or not np.array_equal(out[:, 3], p3):
        raise ValueError("knots moved")
    start2, end2 = curvature(result.x)
    return out, {
        "curvature_jump_before": float(max(abs(end[:-1] - start[1:]))),
        "curvature_jump_after": float(max(abs(end2[:-1] - start2[1:]))),
        "max_handle_change_cells": float(max(abs(result.x - initial))),
        "optimizer_iterations": int(result.nit),
    }
