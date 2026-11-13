"""Preserve the parent's four-point hatched t-axis with a cancelled hole."""

import xml.etree.ElementTree as ET

from ..probability.common import UnsupportedCondition
from .rational_inequality_hatched_svg import signed_intervals
from .rational_inequality_svg import marker, single_canvas


def render(a):
    if (
        len(a.points) != 4
        or len(a.zeros) != 2
        or len(a.poles) != 2
        or len(a.holes) != 1
        or any(p.is_Rational is not True for p in a.points)
    ):
        raise UnsupportedCondition(
            "this source composition requires two rational zeros, one pole and one cancelled hole"
        )
    if any(max(len(str(abs(p.p))), len(str(p.q))) > 3 for p in a.points):
        raise UnsupportedCondition(
            "the reviewed t-axis needs labels of at most three digits"
        )
    width, height, y = 234.4398, 39.7179, 18.928
    if any(p.is_Integer is not True for p in a.points):
        height = 54.6595
    positions = [32.6, 78.0, 127.5, 192.4]
    root = single_canvas(width, height, "hatched_holes", "t")
    signed_intervals(root, a, positions, width, y)
    for point, x in zip(a.points, positions):
        marker(
            root, point, x, y, point not in a.poles and a.sign_operator.endswith("=")
        )
    return ET.tostring(root, encoding="unicode")
