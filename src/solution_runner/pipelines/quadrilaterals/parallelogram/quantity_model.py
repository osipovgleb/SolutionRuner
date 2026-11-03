"""Exact side, height and diagonal quantities in parallelograms and rhombi."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ...triangles.right.altitude_input import _text
from ...triangles.right.altitude_solver import AltitudeSolveError, _parse_positive_value

RULES = {
    "parallelogram-sine-greater-height": "sine",
    "parallelogram-base-height-transfer": "transfer",
    "parallelogram-area-greater-height": "height",
    "rhombus-height-thirty-area": "thirty",
    "rhombus-diagonals-area": "diagonals",
    "rhombus-area-known-diagonal": "other",
    "rhombus-area-diagonal-factor-small": "factor",
    "rhombus-side-sixty-height": "sixty_height",
    "rhombus-side-sixty-long-diagonal": "sixty_diagonal",
    "rhombus-diagonal-ratio-perimeter-height": "ratio_height",
}
PATTERNS = {
    "sine": r"[ВB] параллелограмме ABCD AB\s*=\s*(.+?)\s*,\s*AD\s*=\s*(.+?)\s*,\s*\\sin\s*A\s*=\s*(.+?)\s*\.\s*Найдите большую высоту параллелограмма\s*\.",
    "transfer": r"Стороны параллелограмма равны\s+(.+?)\s+и\s+(.+?)\s*\.\s*Высота, опущенная на (первую сторону|меньшую из этих сторон), равна\s+(.+?)\s*\.\s*Найдите высоту, опущенную на (вторую сторону|большую сторону) параллелограмма\s*\.",
    "height": r"Площадь параллелограмма равна\s+(.+?)\s*,\s*две его стороны равны\s+(.+?)\s+и\s+(.+?)\s*\.\s*Найдите большую высоту этого параллелограмма\s*\.",
    "thirty": r"Найдите площадь ромба, если его высота равна\s+(.+?)\s*,\s*а острый угол(?: равен)?\s+30(?:°|\^\{?\\circ\}?)\s*\.",
    "diagonals": r"Найдите площадь ромба, если его диагонали равны\s+(.+?)\s+и\s+(.+?)\s*\.",
    "other": r"Площадь ромба равна\s+(.+?)\s*\.\s*Одна из его диагоналей равна\s+(.+?)\s*\.\s*Найдите другую диагональ\s*\.",
    "factor": r"Площадь ромба равна\s+(.+?)\s*\.\s*Одна из его диагоналей в\s+(.+?)\s+раз(?:а)? больше другой\s*\.\s*Найдите меньшую диагональ\s*\.",
    "sixty_height": r"Найдите высоту ромба, сторона которого равна\s+(.+?)\s*,\s*а острый угол равен\s*60(?:°|\^\{?\\circ\}?)\s*\.",
    "sixty_diagonal": r"Найдите большую диагональ ромба, сторона которого равна\s+(.+?)\s*,\s*а острый угол равен\s*60(?:°|\^\{?\\circ\}?)\s*\.",
    "ratio_height": r"Диагонали ромба относятся как\s+(.+?)\s*(?::|\\colon)\s*(.+?)\s*\.\s*Периметр ромба равен\s+(.+?)\s*\.\s*Найдите высоту ромба\s*\.",
}


@dataclass(frozen=True)
class Parallelogram:
    mode: str
    given: tuple[sp.Expr, ...]
    a: sp.Expr
    b: sp.Expr
    sine: sp.Expr
    frame: str = "ABCD"
    diagonals: tuple[sp.Expr, ...] = ()

    def name(self, text):
        return text.translate(str.maketrans("ABCD", self.frame))

    @property
    def area(self):
        return sp.simplify(self.a * self.b * self.sine)

    @property
    def first_height(self):
        return sp.simplify(self.b * self.sine)

    @property
    def second_height(self):
        return sp.simplify(self.a * self.sine)

    @property
    def projection(self):
        return sp.simplify(self.b * sp.sqrt(1 - self.sine**2))

    @property
    def answer(self):
        if self.mode in {"thirty", "diagonals"}:
            return self.area
        if self.mode in {"other", "sixty_diagonal"}:
            return self.diagonals[1]
        if self.mode == "factor":
            return self.diagonals[0]
        if self.mode == "transfer":
            return self.second_height
        return sp.simplify(sp.Max(self.first_height, self.second_height))


def _rhombus(mode, given):
    if mode == "thirty":
        return Parallelogram(mode, given, 2 * given[0], 2 * given[0], sp.Rational(1, 2))
    if mode in {"sixty_height", "sixty_diagonal"}:
        side = given[0]
        return Parallelogram(
            mode,
            given,
            side,
            side,
            sp.sqrt(3) / 2,
            diagonals=(side, sp.simplify(side * sp.sqrt(3))),
        )
    if mode == "ratio_height":
        first, second, perimeter = given
        side = perimeter / 4
        scale = side / sp.sqrt(first**2 + second**2)
        diagonals = tuple(sp.simplify(2 * v * scale) for v in given[:2])
    elif mode == "diagonals":
        diagonals = given
    elif mode == "other":
        area, known = given
        diagonals = known, 2 * area / known
    else:
        area, factor = given
        if factor <= 1:
            raise ContentPlanError(
                "one diagonal must be strictly greater than the other"
            )
        small = sp.sqrt(2 * area / factor)
        diagonals = small, factor * small
    first, second = diagonals
    side_squared = sp.simplify((first**2 + second**2) / 4)
    side = sp.sqrt(side_squared)
    return Parallelogram(
        mode,
        given,
        side,
        side,
        sp.simplify(first * second / (2 * side_squared)),
        diagonals=diagonals,
    )


def _model(mode, groups):
    if mode == "transfer":
        first, second, known, height, target = groups
        if (known, target) not in {
            ("первую сторону", "вторую сторону"),
            ("меньшую из этих сторон", "большую сторону"),
        }:
            raise ContentPlanError("the known and requested bases must be distinct")
        given = tuple(_parse_positive_value(v) for v in (first, second, height))
        a, b = given[:2] if known == "первую сторону" else sorted(given[:2])
        return Parallelogram(mode, given, a, b, sp.simplify(given[2] / b))
    given = tuple(_parse_positive_value(v) for v in groups)
    if mode == "sine":
        first, second, sine = given
        return Parallelogram(
            mode,
            given,
            min(first, second),
            max(first, second),
            sine,
            "ABCD" if first <= second else "ADCB",
        )
    if mode == "height":
        area, a, b = given
        return Parallelogram(mode, given, a, b, sp.simplify(area / (a * b)))
    return _rhombus(mode, given)


def read_question(html, source=None):
    try:
        text = _text(html, source, labels="ABCD", extra_identifiers=("ABCD",)).replace(
            "\u0301", ""
        )
        for mode, pattern in PATTERNS.items():
            match = re.fullmatch(pattern, text)
            if match:
                model = _model(mode, match.groups())
                if not 0 < model.sine <= 1:
                    raise ContentPlanError(
                        "the given quantities admit no nondegenerate parallelogram"
                    )
                return model
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError(
        "one complete reviewed parallelogram or rhombus question is required"
    )
