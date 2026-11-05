"""Read complete sphere quantities and compute powers from the actual input kind."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..equations.power_arithmetic import ScalarParser
from ..probability.common import COUNT, UnsupportedCondition, count
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError

GREAT_CIRCLE = r"Площадь большого круга шара равна\s+(.+?)\s*\.\s*Найдите площадь поверхности шара\s*\."
INCREASE = r"Во сколько раз увеличится объем шара, если его радиус увеличить в\s+(.+?)\s+раза?\s*\?"
RATIO = r"(?:Дан[ыо] два шара\.\s*)?(Радиус|Диаметр|Объем) (первого|второго) шара в\s+(.+?)\s+раза? больше (радиуса|диаметра|объема) (первого|второго)\s*\.\s*Во сколько раз площадь поверхности (первого|второго) шара (больше|меньше) площади поверхности (первого|второго)\s*\?"
SUM_VOLUME = r"Радиусы трех шаров равны\s+(.+?)\s*\.\s*Найдите радиус шара, объем которого равен сумме их объемов\s*\."
SUM_AREA = r"Радиусы двух шаров равны\s+(.+?)\s*\.\s*Найдите радиус шара, площадь поверхности которого равна сумме площадей поверхностей двух данных шаров\s*\."
VOLUME_PI = r"Объем шара равен\s+(.+?)\s*\\pi\s*\.\s*Найдите площадь его поверхности, деленную на\s+\\pi\s*\."


@dataclass(frozen=True)
class SphereQuantity:
    mode: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr
    degree: int = 0
    input_kind: str = ""
    large: int = 1
    small: int = 2

    @property
    def radius_ratio(self):
        return sp.simplify(
            self.given[0] ** sp.Rational(1, 3 if self.input_kind == "volume" else 1)
        )


def _positive(raw, *, words=False):
    if re.search(r"\d\s+\d", raw):
        if re.fullmatch(r"[1-9]\d{0,2}(?: \d{3})+(?:[,.]\d+)?", raw) is None:
            raise ContentPlanError("sphere digit groups must be unambiguous thousands")
        raw = raw.replace(" ", "")
    amount = (
        sp.Integer(count(raw))
        if words and re.fullmatch(COUNT, raw)
        else ScalarParser(raw).parse()
    )
    if (
        amount.is_positive is not True
        or amount.is_real is not True
        or amount.is_finite is not True
    ):
        raise ContentPlanError(
            "sphere measurements must be positive finite real values"
        )
    return amount


def _ratio(match):
    kind, large, raw, genitive, small, asked, comparison, other = match.groups()
    names = {"первого": 1, "второго": 2}
    expected = {
        "Радиус": ("радиуса", "radius"),
        "Диаметр": ("диаметра", "diameter"),
        "Объем": ("объема", "volume"),
    }
    if (
        genitive != expected[kind][0]
        or large == small
        or (asked, other)
        != ((large, small) if comparison == "больше" else (small, large))
    ):
        raise ContentPlanError(
            "sphere comparisons must use consistent quantities and directions"
        )
    factor = _positive(raw, words=True)
    if (factor - 1).is_positive is not True:
        raise ContentPlanError("a sphere increase factor must exceed one")
    power = 3 if kind == "Объем" else 1
    return SphereQuantity(
        "surface_factor",
        (factor,),
        sp.simplify(factor ** sp.Rational(2, power)),
        input_kind=expected[kind][1],
        large=names[large],
        small=names[small],
    )


def _read(raw):
    match = re.fullmatch(RATIO, raw)
    if match:
        return _ratio(match)
    for pattern, mode in (
        (GREAT_CIRCLE, "great_circle_surface"),
        (INCREASE, "volume_factor"),
        (VOLUME_PI, "surface_over_pi"),
    ):
        match = re.fullmatch(pattern, raw)
        if not match:
            continue
        amount = _positive(match[1], words=mode == "volume_factor")
        if mode == "volume_factor" and (amount - 1).is_positive is not True:
            raise ContentPlanError("a sphere increase factor must exceed one")
        answer = {
            "great_circle_surface": 4 * amount,
            "volume_factor": amount**3,
            "surface_over_pi": 4 * (3 * amount / 4) ** sp.Rational(2, 3),
        }[mode]
        return SphereQuantity(
            mode, (amount,), sp.simplify(answer), input_kind="radius", large=2, small=1
        )
    for pattern, degree, size in ((SUM_VOLUME, 3, 3), (SUM_AREA, 2, 2)):
        match = re.fullmatch(pattern, raw)
        if not match:
            continue
        parts = re.split(r",\s+|\s+и\s+", match[1])
        if len(parts) != size:
            raise ContentPlanError("the sphere radii list needs explicit separators")
        given = tuple(_positive(p) for p in parts)
        answer = sp.simplify(sum(r**degree for r in given) ** sp.Rational(1, degree))
        return SphereQuantity("combined_radius", given, answer, degree=degree)
    raise ContentPlanError("one complete reviewed sphere question is required")


def read_question(html, source=None):
    if not isinstance(html, str):
        raise ContentPlanError("complete sphere condition HTML is required")
    soup = BeautifulSoup(html, "html.parser")
    for image in soup.find_all("img"):
        if "width" in image.attrs:
            if (
                re.fullmatch(r"[1-9]\d{0,3}", str(image["width"])) is None
                or int(image["width"]) > 4096
            ):
                raise ContentPlanError(
                    "a sphere image width must be a bounded pixel count"
                )
            del image["width"]
    try:
        return _read(_text(str(soup), source, labels="Rr").replace("ё", "е"))
    except (UnsupportedCondition, AltitudeSolveError) as exc:
        raise ContentPlanError(str(exc)) from exc
