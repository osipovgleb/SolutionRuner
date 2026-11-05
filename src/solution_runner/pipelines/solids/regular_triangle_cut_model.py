"""Equal base-edge cuts with a lateral point, with or without the centroid."""

import re
from dataclasses import replace

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import model

MODES = {"regular_triangle_center_cut_area", "regular_triangle_general_cut_area"}
HEADER = (
    r"[ВB] правильной треугольной пирамиде MABC с основанием ABC стороны основания равны (.+?), а боковые ребра (?:[—–-] )?(.+?)\. "
    r"На ребре AC находится точка D, на ребре AB находится точка E, а на ребре AM [—–-] точка L\. Известно, что "
)
CENTER = (
    r"Докажите, что плоскость, проходящая через точки E, D и L, проходит еще и через центр основания пирамиды\. ",
    r"Докажите, что плоскость EDL содержит центр основания пирамиды\. ",
)
AREA = (
    r"Найдите площадь сечения пирамиды этой плоскостью\.",
    r"Найдите площадь сечения пирамиды плоскостью, проходящей через точки E, D и L\.",
)


def _solve(groups, edge, claim):
    a, e, u = map(positive, groups)
    t = u if edge == "AD" else a - u
    al = e - u
    if not (0 < t < a and 0 < al < e):
        raise ContentPlanError("D, E and L must lie inside AC, AB and AM")
    center = sp.simplify(3 * t - 2 * a) == 0
    if claim == "center" and not center:
        raise ContentPlanError("the edge-point plane does not contain the base center")
    q = regular("triangle", {"a": a, "e": e})
    r = al / e
    q.update(
        LM=u,
        AD=t,
        AE=t,
        CD=a - t,
        BE=a - t,
        AL=al,
        fraction=r,
        AK=r * q["R"],
        KO=(1 - r) * q["R"],
        LK=r * q["H"],
        AH=3 * t * q["R"] / (2 * a),
        KH=abs(3 * t / (2 * a) - r) * q["R"],
        DE=t,
        LE2=al * al + t * t - al * t * a / e,
    )
    q["section_height"] = sp.sqrt(q["LE2"] - t * t / 4)
    result = model(
        "regular_triangle_center_cut_area"
        if center
        else "regular_triangle_general_cut_area",
        (("a", a), ("e", e), (edge, u)),
        q,
        (claim, edge),
        t * q["section_height"] / 2,
    )
    foot = "O" if center else "K" if sp.simplify(q["KH"]) == 0 else "H"
    return replace(result, symbols={"section_foot": foot})


def read(raw):
    for edge, other in (("AD", "AE"), ("CD", "BE")):
        given = edge + r"\s*=\s*" + other + r"\s*=\s*LM\s*=\s*(.+?)\. "
        for proof, claim in [(p, "center") for p in CENTER] + [("", "plain")]:
            for area in AREA:
                match = re.fullmatch(HEADER + given + proof + area, raw)
                if match:
                    try:
                        return _solve(match.groups(), edge, claim)
                    except UnsupportedCondition as exc:
                        raise ContentPlanError(
                            "complete numeric section measurements are required"
                        ) from exc
    return None
