"""Restore two lost vertex indices only for one reviewed exact source condition."""

import hashlib

from ..core.errors import ContentPlanError

# The original condition's two formula images explicitly contain the subscript 1.
# https://math-ege.sdamgia.ru/problem?id=245360
SOURCE_SHA256 = "f8715c1faef5b8d262f16f52ad3bbf71b4dc9e3bae9b56889affd1cf31602388"
REPLACEMENTS = (
    ('<var data-math-identifier="D">D</var>', '<span data-inline-latex="D_1"></span>'),
    (
        '<var data-math-identifier="AA">AA</var>',
        '<span data-inline-latex="AA_1"></span>',
    ),
)


def restore_html(html):
    if (
        not isinstance(html, str)
        or hashlib.sha256(html.encode()).hexdigest() != SOURCE_SHA256
    ):
        return html
    for old, new in REPLACEMENTS:
        if html.count(old) != 1:
            raise ContentPlanError("the reviewed source subscript restoration changed")
        html = html.replace(old, new)
    return html
