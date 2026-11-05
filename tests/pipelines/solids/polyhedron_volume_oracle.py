"""Independent exact convex-hull volume from supporting facets and centroid tetrahedra."""

import itertools
from fractions import Fraction


def subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def boundary(points):
    lower = []
    for p in points:
        while (
            len(lower) > 1
            and (
                (lower[-1][0] - lower[-2][0]) * (p[1] - lower[-2][1])
                - (lower[-1][1] - lower[-2][1]) * (p[0] - lower[-2][0])
            )
            <= 0
        ):
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while (
            len(upper) > 1
            and (
                (upper[-1][0] - upper[-2][0]) * (p[1] - upper[-2][1])
                - (upper[-1][1] - upper[-2][1]) * (p[0] - upper[-2][0])
            )
            <= 0
        ):
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def volume(points):
    points = tuple(tuple(Fraction(x) for x in p) for p in points)
    center = tuple(sum(p[i] for p in points) / len(points) for i in range(3))
    facets = {}
    for a, b, c in itertools.combinations(points, 3):
        normal = cross(subtract(b, a), subtract(c, a))
        if not any(normal):
            continue
        distances = [dot(normal, subtract(p, a)) for p in points]
        if min(distances) < 0 < max(distances):
            continue
        face = frozenset(p for p, d in zip(points, distances) if d == 0)
        if face in facets:
            continue
        drop = max(range(3), key=lambda i: abs(normal[i]))
        projection = {tuple(p[i] for i in range(3) if i != drop): p for p in face}
        facets[face] = [projection[v] for v in boundary(sorted(projection))]
    result = Fraction()
    for face in facets.values():
        for b, c in itertools.pairwise(face[1:]):
            result += (
                abs(
                    dot(
                        subtract(face[0], center),
                        cross(subtract(b, center), subtract(c, center)),
                    )
                )
                / 6
            )
    return result
