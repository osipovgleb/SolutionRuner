"""Select the parent's right triangles from actual box axes and vertex pairs."""

from ..core.errors import ContentPlanError
from . import box_coordinates as c


def vertex(point):
    return next(name for name, p in c.VERTICES.items() if tuple(point) == p)


def intermediate(a, b, axis):
    point = list(c.VERTICES[a])
    point[axis] = c.VERTICES[b][axis]
    return vertex(point)


def face_corner(a, b):
    axes = c.axes(a + b)
    return intermediate(a, b, 2 if 2 in axes else axes[0])


def scene(m):
    if m.mode == "edge":
        sizes = sorted(len(c.axes(s)) for s, _ in m.given)
        if sizes != [1, 1, 3]:
            raise ContentPlanError(
                "the parent method requires a space diagonal and two edges"
            )
        known = {c.axes(s)[0] for s, _ in m.given if len(c.axes(s)) == 1}
        axis = c.axes(m.requested)[0]
        if axis in known:
            raise ContentPlanError("the requested edge must be the missing measurement")
        a, b = "B", "D_1"
        p = intermediate(b, a, axis) if axis == 2 else intermediate(a, b, axis)
        face = a + p if len(c.axes(a + p)) == 2 else p + b
        leg = p + b if face == a + p else a + p
        f, g = c.endpoints(face)
        corner = face_corner(f, g)
        return {
            "hyp": a + b,
            "face": face,
            "leg": leg,
            "face_legs": (f + corner, corner + g),
            "right": p,
        }
    if any(len(c.axes(s)) != 1 for s, _ in m.given):
        raise ContentPlanError(
            "the parent distance method requires three edge measurements"
        )
    a, b = c.endpoints(m.requested)
    axes = c.axes(m.requested)
    if len(axes) == 1:
        return {"hyp": a + b}
    if len(axes) == 2:
        p = face_corner(a, b)
        return {"hyp": a + b, "legs": (a + p, p + b), "right": p}
    if c.VERTICES[a][2] > c.VERTICES[b][2]:
        a, b = b, a
    p = intermediate(b, a, 2)
    f, g = a, p
    corner = face_corner(f, g)
    return {
        "hyp": a + b,
        "face": a + p,
        "leg": p + b,
        "face_legs": (f + corner, corner + g),
        "right": p,
    }


def pair(segment):
    return tuple(sorted(c.endpoints(segment)))


def blue(m, role):
    s = scene(m)
    if role == "condition" and m.mode in {"distance", "distance_squared"}:
        return (), ()
    if "face" in s:
        required = (s["hyp"], s["face"])
        allowed = (*required, s["leg"])
    elif "legs" in s:
        required = (s["hyp"],)
        a, b = c.endpoints(s["hyp"])
        p = s["right"]
        d = vertex(
            tuple(
                x + y - z
                for x, y, z in zip(c.VERTICES[a], c.VERTICES[b], c.VERTICES[p])
            )
        )
        allowed = (*required, *s["legs"], a + d, d + b)
    else:
        required = allowed = (s["hyp"],)
    return tuple(pair(v) for v in required), tuple(pair(v) for v in allowed)
