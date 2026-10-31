"""Read a complete single equation without inventing an interval-selection subpart."""

import re

from bs4 import BeautifulSoup, NavigableString

from ..word_problems.common import UnsupportedCondition, section
from .exam_input import FIRST


def read(context):
    content = context.get("normalized_content") or {}
    condition = section(content, "condition")
    if condition is None:
        return None
    soup = BeautifulSoup(condition["html"], "html.parser")
    nodes = [
        n for n in soup.contents if not isinstance(n, NavigableString) or n.strip()
    ]
    if len(nodes) != 1 or getattr(nodes[0], "name", None) != "p":
        return None
    paragraph = nodes[0]
    if content.get("assets") or condition.get("asset_keys") or paragraph.attrs:
        raise UnsupportedCondition(
            "a complete text-only single equation paragraph is required"
        )
    formulas = paragraph.select("span[data-inline-latex]")
    if len(formulas) != 1 or any(
        n is not paragraph
        and (
            n is not formulas[0]
            or set(n.attrs) != {"data-inline-latex"}
            or n.get_text(strip=True)
        )
        for n in soup.find_all(True)
    ):
        raise UnsupportedCondition(
            "the single equation must have exactly one unchanged formula"
        )
    formula = formulas[0]["data-inline-latex"]
    formulas[0].replace_with("ФОРМУЛА")
    text = " ".join(
        paragraph.get_text(" ", strip=True)
        .replace("\xad", "")
        .replace("ё", "е")
        .split()
    )
    text = re.sub(r"\s+([.,:;])", r"\1", text)
    if not re.fullmatch(FIRST, text):
        raise UnsupportedCondition("the entire single-equation instruction must match")
    return (
        tuple(section(content, key) for key in ("condition", "answer", "solution")),
        formula,
        None,
        None,
    )


def validate_circle(entry, a):
    from .exam_trigonometric import select
    from .exam_trigonometric_inverse import decode

    if (
        a.scale != 1
        or a.translation
        or entry.get("selection_kind") != "all_roots"
        or entry.get("bounds") is not None
        or entry.get("labels") != []
        or tuple(decode(q) for q in entry["residues"])
        != select(a.series, (0, 2, True, False))[0]
    ):
        raise UnsupportedCondition(
            "a single-part equation needs an audited full-root circle without interval labels"
        )


def render(a, image, intro, steps):
    from ..word_problems.water_season_proof import inline
    from .exam_trigonometric_proof import families, method_notes
    from .exam_trigonometric_variants import root_notation

    if a.image_position == "selection":
        raise UnsupportedCondition(
            "single-part equations have no interval-selection figure"
        )
    parameter = (
        a.square_difference.parameter
        if a.square_difference is not None
        else a.parameter
    )
    all_roots = (
        r";\ ".join(families(a)) + r",\ " + parameter + r"\in\mathbb Z"
        if a.series
        else r"\varnothing"
    )
    html = (
        (image if a.image_position in ("outside", "before-intro") else "")
        + intro
        + (image if a.image_position == "after-intro" else "")
        + steps
        + (image if a.image_position == "after-steps" else "")
        + method_notes(a)
    )
    return root_notation(a, (all_roots, "<p>" + inline(all_roots) + ".</p>", html))
