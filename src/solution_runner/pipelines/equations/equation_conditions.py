"""Read the complete instruction around one normalized elementary equation."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

_PROMPT = (
    r"(?:(?:Найдите корень уравнения|Найдите решение уравнения|Решите уравнение|Решите):? )?"
    r"FORMULA\.?"
)
_SELECTOR = (
    r"(?: Если уравнение имеет (?:более|больше) одного корня, "
    r"(?:укажите|в ответ(?:е)? (?:запишите|укажите)) (?:меньший|больший) "
    r"(?:из них|из корней|корень)\.?)?"
)


def read_equation_prompt(
    html: str,
    *,
    allow_selector: bool = False,
    error_type: type[ValueError] = ValueError,
) -> str:
    soup = BeautifulSoup(html, "html.parser")
    spans = soup.find_all("span")
    if (
        len(spans) != 1
        or spans[0].get_text(strip=True)
        or set(spans[0].attrs) != {"data-inline-latex"}
    ):
        raise error_type("condition needs one unambiguous normalized formula")
    formula = str(spans[0]["data-inline-latex"])
    spans[0].replace_with("FORMULA")
    visible = re.sub(
        r"\s+\.",
        ".",
        " ".join(soup.get_text(" ", strip=True).replace("\u00ad", "").split()),
    )
    if re.fullmatch(_PROMPT + (_SELECTOR if allow_selector else ""), visible) is None:
        raise error_type("unsupported elementary equation instruction")
    return formula
