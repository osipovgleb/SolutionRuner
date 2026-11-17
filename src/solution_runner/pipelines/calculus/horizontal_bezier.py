"""Scoped G2 fit with analytic derivatives for steep horizontal-tangent graphs."""

import numpy as np
from scipy.optimize import minimize

from .primitive_bezier import verify


def _cross(a, b):
    return a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]


class _CurveFit:
    """Geometry and constraints for one connected set of cubic segments."""

    def __init__(self, segments):
        self.n = len(segments)
        self.p0, self.p3 = segments[:, 0], segments[:, 3]
        v0, v1 = segments[:, 1] - self.p0, self.p3 - segments[:, 2]
        l0, l1 = np.linalg.norm(v0, axis=1), np.linalg.norm(v1, axis=1)
        self.u0, self.u1 = v0 / l0[:, None], v1 / l1[:, None]
        if np.max(np.linalg.norm(self.u1[:-1] - self.u0[1:], axis=1)) > 1e-6:
            raise ValueError("mismatched tangents")
        self.initial = np.column_stack((l0, l1)).ravel()
        self.scales = np.repeat(np.linalg.norm(self.p3 - self.p0, axis=1), 2)
        self.start, self.end = self.curvature(self.initial)
        self.kscale = 1 + np.maximum(abs(self.end[:-1]), abs(self.start[1:]))
        self.sign = np.sign(self.p3[:, 1] - self.p0[:, 1])

    def curves(self, z):
        lengths = z.reshape(self.n, 2)
        return np.stack(
            (
                self.p0,
                self.p0 + self.u0 * lengths[:, 0, None],
                self.p3 - self.u1 * lengths[:, 1, None],
                self.p3,
            ),
            axis=1,
        )

    def curvature(self, z):
        lengths = z.reshape(self.n, 2)
        a = (
            (2 / 3)
            * _cross(self.u0, self.p3 - self.p0 - self.u1 * lengths[:, 1, None])
            / lengths[:, 0] ** 2
        )
        b = (
            (2 / 3)
            * _cross(self.u1, self.p0 - self.p3 + self.u0 * lengths[:, 0, None])
            / lengths[:, 1] ** 2
        )
        return a, b

    def equal(self, z):
        a, b = self.curvature(z)
        return (b[:-1] - a[1:]) / self.kscale

    def monotone(self, z):
        delta = np.diff(self.curves(z), axis=1)
        return np.concatenate(
            (delta[:, :, 0].ravel(), (delta[:, :, 1] * self.sign[:, None]).ravel())
        )

    def objective(self, z):
        return np.sum(((z - self.initial) / self.scales) ** 2)

    def objective_jac(self, z):
        return 2 * (z - self.initial) / self.scales**2

    def equal_jac(self, z):
        lengths = z.reshape(self.n, 2)
        a, b = self.curvature(z)
        du = _cross(self.u0, self.u1)
        jac = np.zeros((self.n - 1, 2 * self.n))
        for i in range(self.n - 1):
            jac[i, 2 * i] = -(2 / 3) * du[i] / lengths[i, 1] ** 2 / self.kscale[i]
            jac[i, 2 * i + 1] = -2 * b[i] / lengths[i, 1] / self.kscale[i]
            jac[i, 2 * i + 2] = 2 * a[i + 1] / lengths[i + 1, 0] / self.kscale[i]
            jac[i, 2 * i + 3] = (
                (2 / 3) * du[i + 1] / lengths[i + 1, 0] ** 2 / self.kscale[i]
            )
        return jac

    def monotone_jac(self, z):
        jac = np.zeros((6 * self.n, 2 * self.n))
        for i in range(self.n):
            for coordinate, scale in ((0, 1), (1, self.sign[i])):
                row = 3 * self.n * coordinate + 3 * i
                jac[row, 2 * i] = self.u0[i, coordinate] * scale
                jac[row + 1, 2 * i] = -self.u0[i, coordinate] * scale
                jac[row + 1, 2 * i + 1] = -self.u1[i, coordinate] * scale
                jac[row + 2, 2 * i + 1] = self.u1[i, coordinate] * scale
        return jac

    def upper_bounds(self):
        upper = []
        for i in range(self.n):
            for direction in (self.u0[i], self.u1[i]):
                upper.append(
                    min(
                        abs((self.p3[i, j] - self.p0[i, j]) / direction[j])
                        for j in (0, 1)
                        if abs(direction[j]) > 1e-9
                    )
                    * 0.999
                )
        return upper


def harmonize(s):
    fit = _CurveFit(s)
    result = minimize(
        fit.objective,
        fit.initial,
        method="SLSQP",
        jac=fit.objective_jac,
        bounds=list(zip(np.maximum(fit.scales * 0.03, 1e-6), fit.upper_bounds())),
        constraints=[
            {"type": "eq", "fun": fit.equal, "jac": fit.equal_jac},
            {"type": "ineq", "fun": fit.monotone, "jac": fit.monotone_jac},
        ],
        options={"maxiter": 1000, "ftol": 1e-11},
    )
    if (
        not result.success
        or max(abs(fit.equal(result.x))) > 1e-6
        or min(fit.monotone(result.x)) < -1e-8
    ):
        raise ValueError("curvature optimization: " + str(result.message))
    out = fit.curves(result.x)
    verify(out)
    if not np.array_equal(out[:, 0], fit.p0) or not np.array_equal(out[:, 3], fit.p3):
        raise ValueError("knots moved")
    start2, end2 = fit.curvature(result.x)
    return out, {
        "curvature_jump_before": float(max(abs(fit.end[:-1] - fit.start[1:]))),
        "curvature_jump_after": float(max(abs(end2[:-1] - start2[1:]))),
        "max_handle_change_cells": float(max(abs(result.x - fit.initial))),
        "optimizer_iterations": int(result.nit),
    }
