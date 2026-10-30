"""Keep generated derivations vertical without splitting nested math systems."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

_TOKEN = re.compile(
    r"\\begin\{(?P<begin>[^}]+)\}|\\end\{(?P<end>[^}]+)\}|\\[{}]|[{}]|\\iff\s*"
)


def _steps(formula: str) -> list[str]:
    depth = 0
    environments = []
    start = 0
    result = []
    for match in _TOKEN.finditer(formula):
        token = match.group()
        if match["begin"]:
            environments.append(match["begin"])
        elif match["end"]:
            if not environments or environments.pop() != match["end"]:
                raise ValueError("unbalanced math environment in generated solution")
        elif token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced braces in generated solution")
        elif token.startswith(r"\iff") and depth == 0 and not environments:
            result.append(formula[start : match.start()].strip())
            start = match.end()
    if depth or environments:
        raise ValueError("unbalanced generated derivation")
    result.append(formula[start:].strip())
    if any(not step for step in result):
        raise ValueError("empty step in generated derivation")
    return result


def vertical_derivation(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for span in list(soup.select("span[data-inline-latex]")):
        formula = str(span["data-inline-latex"])
        if r"\iff" not in formula:
            continue
        paragraph = span.parent
        if paragraph.name != "p" or paragraph.find_parent("center") is None:
            continue
        if len(paragraph.select("span[data-inline-latex]")) != 1:
            continue
        punctuation = paragraph.get_text("", strip=True)
        if punctuation not in ("", ".", ","):
            continue
        steps = _steps(formula)
        if len(steps) < 2:
            continue
        replacements = []
        for index, step in enumerate(steps):
            row = soup.new_tag("p", attrs=dict(paragraph.attrs))
            math = soup.new_tag("span", attrs=dict(span.attrs))
            math["data-inline-latex"] = step
            row.append(math)
            if index == len(steps) - 1:
                row.append(punctuation)
            replacements.append(row)
        paragraph.replace_with(*replacements)
    return str(soup)
