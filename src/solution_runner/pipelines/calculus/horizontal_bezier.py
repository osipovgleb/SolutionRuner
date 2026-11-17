"""Scoped G2 fit with analytic derivatives for steep horizontal-tangent graphs."""

import numpy as np
from scipy.optimize import minimize

from .primitive_bezier import verify


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

    def objective_jac(z):
        return 2 * (z - initial) / scales**2

    def equal_jac(z):
        l = z.reshape(n, 2)
        a, b = curvature(z)
        du = cross(u0, u1)
        jac = np.zeros((n - 1, 2 * n))
        for i in range(n - 1):
            jac[i, 2 * i] = -(2 / 3) * du[i] / l[i, 1] ** 2 / kscale[i]
            jac[i, 2 * i + 1] = -2 * b[i] / l[i, 1] / kscale[i]
            jac[i, 2 * i + 2] = 2 * a[i + 1] / l[i + 1, 0] / kscale[i]
            jac[i, 2 * i + 3] = (2 / 3) * du[i + 1] / l[i + 1, 0] ** 2 / kscale[i]
        return jac

    def monotone_jac(z):
        jac = np.zeros((6 * n, 2 * n))
        for i in range(n):
            for coordinate, scale in ((0, 1), (1, sign[i])):
                row = 3 * n * coordinate + 3 * i
                jac[row, 2 * i] = u0[i, coordinate] * scale
                jac[row + 1, 2 * i] = -u0[i, coordinate] * scale
                jac[row + 1, 2 * i + 1] = -u1[i, coordinate] * scale
                jac[row + 2, 2 * i + 1] = u1[i, coordinate] * scale
        return jac

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
        jac=objective_jac,
        bounds=list(zip(np.maximum(scales * 0.03, 1e-6), upper)),
        constraints=[
            {"type": "eq", "fun": equal, "jac": equal_jac},
            {"type": "ineq", "fun": monotone, "jac": monotone_jac},
        ],
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
