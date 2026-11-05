"""Construct reviewed orthogonal topologies and geometrically prove parent partitions."""

from dataclasses import dataclass

from ..core.errors import ContentPlanError
from ..probability.common import UnsupportedCondition
from .measurements import positive
from .orthogonal_geometry import Cuboid, OrthogonalSolid


@dataclass(frozen=True)
class Shape:
    solid: OrthogonalSolid
    parts: tuple[Cuboid, ...]
    method: str
    differences: tuple[tuple, ...] = ()

    @property
    def answer(self):
        return self.solid.volume


def block(size, origin=(0, 0, 0)):
    return Cuboid(tuple(origin), tuple(x + d for x, d in zip(origin, size)))


def assembled(additions, *, cutouts=(), parts=None, differences=()):
    method = "subtract" if cutouts else "add"
    parts = additions + cutouts if parts is None else parts
    solid = OrthogonalSolid(additions, cutouts)
    if method == "subtract":
        if len(parts) != 2:
            raise ContentPlanError("this subtraction method requires one removed box")
        witness = OrthogonalSolid((parts[0],), (parts[1],))
        total = parts[0].volume - parts[1].volume
    else:
        if len(parts) not in (2, 3):
            raise ContentPlanError("this addition method requires two or three boxes")
        witness = OrthogonalSolid(parts)
        total = sum(p.volume for p in parts)
    if total != witness.volume or not solid.equivalent(witness):
        raise ContentPlanError(
            "the parent partition overlaps, misses or relocates material"
        )
    return Shape(solid, parts, method, differences)


def step_width(g):
    x, y, h, low, right = g
    left = block((x - right, y, h))
    lower = block((right, y, low), (x - right, 0, 0))
    if low >= h:
        raise ContentPlanError("the lower step must be below the upper step")
    return assembled((left, lower), differences=((x, right),))


def step_rise(g):
    x, y, h, rise, left = g
    tall = block((left, y, h))
    right = block((x - left, y, h - rise), (left, 0, 0))
    base = block((x, y, h - rise))
    top = block((left, y, rise), (0, 0, h - rise))
    return assembled((tall, right), parts=(base, top), differences=((h, rise),))


def depth_step(g):
    x, y, h, rise, front = g
    back = block((x, y - front, h), (0, front, 0))
    lower = block((x, front, h - rise))
    return assembled((back, lower), differences=((y, front), (h, rise)))


def plan_step(g):
    x, y, h, right, depth = g
    outer = block((x, y, h))
    cut = block((right, depth, h), (x - right, 0, 0))
    left = block((x - right, y, h))
    back = block((right, y - depth, h), (x - right, depth, 0))
    result = assembled((left, back), differences=((x, right), (y, depth)))
    if not result.solid.equivalent(OrthogonalSolid((outer,), (cut,))):
        raise ContentPlanError("the L-shaped base differs from its corner cut")
    return result


def upper_corner_left(g):
    x, y, h, width, depth, low = g
    if width >= x or depth >= y or low >= h:
        raise ContentPlanError(
            "the upper corner must leave material along all three axes"
        )
    return assembled(
        (block((x, y, h)),),
        cutouts=(block((width, depth, h - low), (0, 0, low)),),
        differences=((h, low),),
    )


def front_notch(g):
    x, y, h, width, depth = g
    if width >= x or depth >= y:
        raise ContentPlanError(
            "the front notch must leave two side arms and a back wall"
        )
    return assembled(
        (block((x, y, h)),),
        cutouts=(block((width, depth, h), ((x - width) / 2, 0, 0)),),
    )


def front_groove(g):
    x, y, h, depth, height = g
    if depth >= y or height >= h:
        raise ContentPlanError(
            "the groove must leave a back wall and two horizontal arms"
        )
    return assembled(
        (block((x, y, h)),),
        cutouts=(block((x, depth, height), (0, 0, (h - height) / 2)),),
    )


def bar(g):
    x, y, h, width, rise = g
    if width >= x:
        raise ContentPlanError("the top bar must leave both shoulders of the base")
    base = block((x, y, h))
    top = block((width, y, rise), ((x - width) / 2, 0, h))
    return assembled((base, top))


def shelf(g):
    x, y, h, width, height = g
    if height >= h:
        raise ContentPlanError("the shelf must fit between the tall box's ends")
    tall = block((x, y, h))
    side = block((width, y, height), (x, 0, (h - height) / 2))
    return assembled((tall, side), parts=(side, tall))


def through_plate(g):
    x, y, h, width, height = g
    if width >= x or height >= h:
        raise ContentPlanError(
            "the through-hole must have a positive frame on all sides"
        )
    return assembled(
        (block((x, y, h)),),
        cutouts=(block((width, y, height), ((x - width) / 2, 0, (h - height) / 2)),),
    )


def pedestal(g):
    x, y, h, width, depth, rise = g
    if width >= x or depth >= y:
        raise ContentPlanError("the upper pedestal must fit within its wider base")
    base = block((x, y, h - rise))
    top = block((width, depth, rise), (0, y - depth, h - rise))
    return assembled((base, top), parts=(top, base), differences=((h, rise),))


def side_boxes(g):
    x, left, depth, height, right_depth, right_height = g
    if depth >= right_depth or height >= right_height:
        raise ContentPlanError(
            "the tall side must exceed the lower side in depth and height"
        )
    low = block((left, depth, height))
    tall = block((x - left, right_depth, right_height), (left, 0, 0))
    return assembled((low, tall), parts=(tall, low), differences=((x, left),))


def right_wing(g):
    x, left, depth, back, h, rise = g
    if back >= depth:
        raise ContentPlanError(
            "the lower left base must protrude beyond the back strip"
        )
    base = block((left, depth, h - rise))
    top = block((left, back, rise), (0, depth - back, h - rise))
    side = block((x - left, back, h - rise), (left, depth - back, 0))
    return assembled(
        (base, top, side), parts=(top, base, side), differences=((h, rise), (x, left))
    )


def left_wing(g):
    x, main, depth, back, h, rise = g
    if x <= main or back >= depth:
        raise ContentPlanError(
            "the left wing and front strip must have positive widths"
        )
    low = h - rise
    base = block((main, depth, low))
    side = block((x - main, back, low), (main - x, depth - back, 0))
    top = block((main, back, rise), (0, depth - back, low))
    rear = block((x, back, low), (main - x, depth - back, 0))
    front = block((main, depth - back, low))
    return assembled(
        (base, side, top),
        parts=(top, rear, front),
        differences=((h, rise), (depth, back)),
    )


def upper_corner_right(g):
    x, y, h, width, depth, height = g
    if width >= x or depth >= y or height >= h:
        raise ContentPlanError(
            "the upper corner must leave material along all three axes"
        )
    return assembled(
        (block((x, y, h)),),
        cutouts=(block((width, depth, height), (x - width, 0, h - height)),),
    )


SHAPES = {
    "step_width": (5, step_width),
    "step_rise": (5, step_rise),
    "depth_step": (5, depth_step),
    "plan_step": (5, plan_step),
    "upper_corner_left": (6, upper_corner_left),
    "front_notch": (5, front_notch),
    "front_groove": (5, front_groove),
    "bar": (5, bar),
    "shelf": (5, shelf),
    "through_plate": (5, through_plate),
    "pedestal": (6, pedestal),
    "side_boxes": (6, side_boxes),
    "right_wing": (6, right_wing),
    "left_wing": (6, left_wing),
    "upper_corner_right": (6, upper_corner_right),
}


def build(kind, given):
    if (
        kind not in SHAPES
        or not isinstance(given, (tuple, list))
        or len(given) != SHAPES[kind][0]
    ):
        raise ContentPlanError(
            "a complete reviewed orthogonal measurement set is required"
        )
    try:
        return SHAPES[kind][1](tuple(positive(str(v)) for v in given))
    except UnsupportedCondition as exc:
        raise ContentPlanError(str(exc)) from exc
