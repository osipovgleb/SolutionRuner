"""Read complete numeric-diagram volume questions before constructing the solid."""

import re

from ..core.errors import ContentPlanError
from .orthogonal_shapes import build
from .orthogonal_sources import DATA, source_bytes
from .prism_input import text


def read(html, source):
    raw = text(html, source)
    if (
        re.fullmatch(
            r"Найдите объем многогранника, изображенного на рисунке \(все двугранные углы (?:многогранника )?прямые\)\.",
            raw,
        )
        is None
    ):
        raise ContentPlanError(
            "one complete reviewed orthogonal volume question is required"
        )
    source_bytes(source)
    review = DATA["figures"][source]
    return build(review["shape"], review["given"]), review["shape"]
