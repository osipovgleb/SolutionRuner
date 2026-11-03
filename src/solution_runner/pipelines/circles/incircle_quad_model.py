"""One opposite-side-sum relation, selected by the complete requested quantity."""

import sympy as sp

from ..core.errors import ContentPlanError

PATTERNS = {
    "perimeter": r"[ВB] четырехугольник ABCD\s+вписана окружность\s*,\s*AB\s*=\s*(.+?)\s*,\s*CD\s*=\s*(.+?)\s*\.\s*Найдите периметр четырехугольника ABCD\s*\.",
    "fourth_side": r"[ВB] четырехугольник ABCD\s+вписана окружность\s*,\s*AB\s*=\s*(.+?)\s*,\s*BC\s*=\s*(.+?)\s+и\s+CD\s*=\s*(.+?)\s*\.\s*Найдите четвертую сторону четырехугольника\s*\.",
    "opposite_side": r"[ВB] четырехугольник ABCD\s*,\s*периметр которого равен\s+(.+?)\s*,\s*вписана окружность\s*,\s*AB\s*=\s*(.+?)\s*\.\s*Найдите (?:длину стороны\s+)?CD\s*\.",
    "larger_side": r"Периметр четырехугольника, описанного около окружности, равен\s+(.+?)\s*,\s*две его стороны равны\s+(.+?)\s+и\s+(.+?)\s*\.\s*Найдите большую из оставшихся сторон\s*\.",
}


def solve(target, given):
    if target == "perimeter":
        return 2 * sum(given)
    if target == "fourth_side":
        result = given[0] + given[2] - given[1]
    elif target == "opposite_side":
        result = given[0] / 2 - given[1]
    else:
        perimeter, a, b = given
        if a + b == perimeter / 2:
            raise ContentPlanError(
                "the unnamed sides may be opposite; the remaining lengths are undetermined"
            )
        remaining = (perimeter / 2 - a, perimeter / 2 - b)
        if any(v.is_positive is not True for v in remaining):
            raise ContentPlanError("all four tangential sides must be positive")
        result = sp.Max(*remaining)
    if result.is_positive is not True:
        raise ContentPlanError("all four tangential sides must be positive")
    return sp.simplify(result)
