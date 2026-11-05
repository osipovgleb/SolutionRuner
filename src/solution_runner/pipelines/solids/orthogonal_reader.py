"""Read complete numeric-diagram questions before constructing the solid."""

import re

from ..core.errors import ContentPlanError
from .orthogonal_shapes import build
from .orthogonal_sources import DATA, source_bytes
from .prism_input import text


def read(html, source, *, quantity="volume"):
    if quantity not in {"volume", "surface"}:
        raise ContentPlanError("an explicit reviewed solid quantity is required")
    target = "объем" if quantity == "volume" else "площадь поверхности"
    raw = text(html, source)
    if (
        re.fullmatch(
            rf"Найдите {target} многогранника, изображенного на рисунке \(все двугранные углы (?:многогранника )?прямые\)\.",
            raw,
        )
        is None
    ):
        raise ContentPlanError(
            "one complete reviewed orthogonal quantity question is required"
        )
    source_bytes(source)
    review = DATA["figures"][source]
    return build(review["shape"], review["given"]), review["shape"]
