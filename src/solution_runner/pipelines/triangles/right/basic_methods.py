"""Recognize complete reviewed methods for elementary right-triangle questions."""

import re

from bs4 import BeautifulSoup

from .altitude_methods import review_sections
from .altitude_solver import AltitudeSolveError

_BLUEPRINTS = (
    (
        "sine_hypotenuse",
        r"\cosA=\sqrt{1-\sin^2A}=",
        (
            (
                "Решение",
                (
                    r"\cosA=\sqrt{1-\sin^2A}=",
                    r"AB=\frac{AC}{\cosA}=",
                    re.compile(r"\\cosA=\\frac\{\d+\}\{\d+\}=\\frac\{AC\}\{AB\}"),
                    re.compile(r"\\frac\{\d+\}\{\d+\}=\\frac\{[\d{,}.]+\}\{AB\}"),
                    r"AB=\frac{",
                ),
            ),
            (
                "Приведём другое решение",
                (
                    r"\sinA=\frac{CB}{AB}=",
                    r"\frac{CB}{x}=",
                    r"CB=\frac{",
                    re.compile(r"x\^2=[^=]+\+\(\\frac\{\d+\}\{\d+\}x\)\^2\\iff"),
                ),
            ),
        ),
    ),
    (
        "sine_opposite",
        r"BC=AC\tgA=\frac{AC\sinA}",
        (
            ("Решение", (r"BC=AC\tgA=\frac{AC\sinA}{\sqrt{1-\sin^2A}}=",)),
            (
                "Альтернативное решение.",
                (
                    r"\cosA=\sqrt{1-\sin^2A}=",
                    r"AB=\frac{AC}{\cosA}=",
                    r"BC=\sqrt{AB^2-AC^2}=",
                ),
            ),
        ),
    ),
    (
        "cosine_hypotenuse",
        r"\cosA=\frac{AC}{AB}=",
        (
            (
                "Решение",
                (
                    r"\cosA=\frac{AC}{AB}=",
                    re.compile(r"\\frac\{\d+\}\{AB\}="),
                    r"AB=\frac{",
                    r"AB=\frac{AC}{\cosA}=",
                ),
            ),
        ),
    ),
    (
        "tangent_hypotenuse",
        r"\tgA=\frac{BC}{AC}",
        (
            (
                "Приведем другое решение:",
                (r"\tgA=\frac{BC}{AC}", r"BC=AC\cdot\tgA=", r"AB=\sqrt{AC^2+BC^2}="),
            ),
        ),
    ),
    ("tangent_opposite", r"BC=AC\tgA=", (("Решение", (r"BC=AC\tgA=",)),)),
    (
        "sine_from_opposite",
        r"AB=\frac{BC}{\sinA}=",
        (("Решение", (r"AB=\frac{BC}{\sinA}=",)),),
    ),
    (
        "cosine_adjacent",
        r"AC=\frac{BC}{\tgA}=\frac{BC\cosA}",
        (
            (
                "Решение",
                (
                    r"AC=\frac{BC}{\tgA}=\frac{BC\cosA}{\sinA}=\frac{BC\cosA}{\sqrt{1-\cos^2A}}=",
                ),
            ),
        ),
    ),
    (
        "tangent_adjacent",
        r"AC=\frac{BC}{\tgA}=",
        (("Решение", (r"AC=\frac{BC}{\tgA}=",)),),
    ),
    (
        "sine_from_legs",
        r"\sinA=\frac{BC}{AB}=\frac{BC}{\sqrt{BC^2+AC^2}}=",
        (("Решение", (r"\sinA=\frac{BC}{AB}=\frac{BC}{\sqrt{BC^2+AC^2}}=",)),),
    ),
)

_SIGNATURES = {
    "sine_hypotenuse": (("AB", {"AC", "sinA"}), ("AC", {"AB", "sinA"})),
    "sine_opposite": (("BC", {"AC", "sinA"}),),
    "cosine_hypotenuse": (("AB", {"AC", "cosA"}),),
    "tangent_hypotenuse": (("AB", {"AC", "tgA"}), ("AC", {"AB", "tgA"})),
    "tangent_opposite": (("BC", {"AC", "tgA"}),),
    "sine_from_opposite": (("AB", {"BC", "sinA"}),),
    "cosine_adjacent": (("AC", {"BC", "cosA"}),),
    "tangent_adjacent": (("AC", {"BC", "tgA"}), ("AC", {"AB", "tgA"})),
    "sine_from_legs": (("sinA", {"AC", "BC"}),),
}


def read_parent(html):
    soup = BeautifulSoup(html, "html.parser")
    if soup.find(["img", "script", "style"]):
        raise AltitudeSolveError("the complete basic-triangle parent must be reviewed")
    for node in soup.select("[data-inline-latex]"):
        node["data-inline-latex"] = (
            "".join(node["data-inline-latex"].split())
            .replace("^{2}", "^2")
            .replace(r"\operatorname{tg}", r"\tg")
        )
    first = soup.select_one("[data-inline-latex]")
    if first is None:
        raise AltitudeSolveError(
            "the parent must contain a reviewed mathematical method"
        )
    if not soup.select('section[data-content-kind="solution"]'):
        wrapper = soup.new_tag(
            "section",
            attrs={"data-content-kind": "solution", "data-solution-title": "Решение"},
        )
        for node in list(soup.contents):
            wrapper.append(node.extract())
        soup.append(wrapper)
    for kind, prefix, sections in _BLUEPRINTS:
        if first["data-inline-latex"].startswith(prefix):
            review_sections(soup, sections)
            return kind
    raise AltitudeSolveError(
        "the complete basic-triangle parent method has not been reviewed"
    )


def validate_child(kind, solved):
    signature = (solved.requested, {k for k, _, _ in solved.givens})
    if signature not in _SIGNATURES[kind]:
        raise AltitudeSolveError("the child requires a different right-triangle method")
