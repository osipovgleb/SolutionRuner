"""Read the complete altitude question across prose, math spans and figure gaps."""

import re
import unicodedata
from html import escape

from bs4 import BeautifulSoup

from .altitude_solver import AltitudeSolveError, _parse_positive_value, _split_braced

_LABELS = str.maketrans(
    {"А": "A", "В": "B", "С": "C", "Н": "H", "М": "M", "Д": "D", "Е": "E", "О": "O"}
)
_ALIASES = {"BA": "AB", "CA": "AC", "CB": "BC", "HA": "AH", "HB": "BH", "HC": "CH"}
_QUANTITY = r"(?:AB|BA|AC|CA|BC|CB|AH|HA|BH|HB|CH|HC|\\(?:sin|cos|tg)\s*[AB])"


def _key(text):
    compact = text.replace(" ", "")
    return compact[1:] if compact.startswith("\\") else _ALIASES.get(compact, compact)


def _value(text):
    text = text.lstrip()
    if text.startswith(r"\frac"):
        end = len(r"\frac")
        for _ in range(2):
            while end < len(text) and text[end].isspace():
                end += 1
            _, end = _split_braced(text, end)
    else:
        match = re.match(
            r"(?:\d+(?:(?:[,.]|\{,\})\d+)?)?\s*\\sqrt\s*\{\d+\}|\d+(?:(?:[,.]|\{,\})\d+)?",
            text,
        )
        if match is None:
            raise AltitudeSolveError("one complete positive exact value is required")
        end = match.end()
    raw = text[:end].replace(" ", "").replace("{,}", ".").replace(",", ".")
    _parse_positive_value(raw)
    rest = text[end:]
    if rest and not re.match(r"[\s,.;:]", rest):
        raise AltitudeSolveError("an exact value must end at a statement boundary")
    return raw.replace(".", "{,}"), rest


def _text(html, source, *, labels="ABCH"):
    alphabet = labels + "".join(chr(k) for k, v in _LABELS.items() if v in labels)
    soup = BeautifulSoup(html, "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise AltitudeSolveError("one audited condition figure is required")
    for tag in list(soup.find_all(True)):
        if tag.name == "img":
            if (
                tag.get("data-asset-id") != source
                or tag.get("data-asset-key") != "image_1"
                or tag.get("src") != "/assets/" + source
                or set(tag.attrs)
                - {
                    "alt",
                    "src",
                    "data-asset-id",
                    "data-asset-key",
                    "data-transformation-target-id",
                }
            ):
                raise AltitudeSolveError("the condition figure identity changed")
            tag.decompose()
        elif tag.name == "span" and set(tag.attrs) == {"data-inline-latex"}:
            if tag.get_text().strip() or not tag["data-inline-latex"]:
                raise AltitudeSolveError("ambiguous mathematical markup")
            tag.replace_with(" " + tag["data-inline-latex"] + " ")
        elif tag.name == "var":
            value = tag.get_text().translate(_LABELS)
            if (
                set(tag.attrs) != {"data-math-identifier"}
                or tag["data-math-identifier"].translate(_LABELS) != value
                or not re.fullmatch(rf"[{labels}]{{1,3}}", value)
            ):
                raise AltitudeSolveError("unsupported geometric identifier")
            tag.replace_with(" " + value + " ")
        elif (
            tag.name
            not in {"p", "br", "figure", "center", "nobr", "i", "em", "b", "strong"}
            or tag.attrs
        ):
            raise AltitudeSolveError("unsupported complete altitude markup")
    text = unicodedata.normalize("NFKC", soup.get_text(" ", strip=True))
    text = text.replace("\xad", "").replace("\u2060", "").replace("\u200b", "")
    text = re.sub(rf"\b[{alphabet}]{{1,3}}\b", lambda m: m[0].translate(_LABELS), text)
    text = text.replace(r"\operatorname{tg}", r"\tg").replace(r"\tan", r"\tg")
    text = text.replace(r"\quad", ", ").replace(r"\;", " ")
    return " ".join(text.split())


def canonical_condition(html, *, source):
    """Validate every statement and adapt it only in memory for the shared solver."""
    text = _text(html, source)
    if text.count("Найдите") != 1:
        raise AltitudeSolveError("exactly one complete altitude question is required")
    given, _, question = text.partition("Найдите")
    request = re.fullmatch(
        rf"\s*(?:длину\s+)?(?:отрезка\s+|высоту\s+)?({_QUANTITY})\s*\.?\s*", question
    )
    if request is None:
        raise AltitudeSolveError("unsupported complete altitude request")
    requested = _key(request[1])
    setup = re.match(
        r"[ВB] (?:прямоугольном )?треугольнике ABC\s*[:,]?\s*(?:угол C равен\s*|\\angle\s*C\s*=\s*)90(?:°|\^\{?\\circ\}?)?",
        given,
    )
    if setup is None:
        raise AltitudeSolveError("angle C must be explicitly right")
    rest = given[setup.end() :].lstrip()
    if not rest or rest[0] not in ",.;:":
        raise AltitudeSolveError("the right-angle statement must be complete")
    values, altitude = {}, False
    while rest.strip(" ,.;:"):
        rest = rest.lstrip(" ,.;:")
        rest = re.sub(r"^и\s+", "", rest)
        height = re.match(r"CH\s*[—–−-]?\s*высот[ау]\b", rest)
        if height:
            altitude, rest = True, rest[height.end() :]
            continue
        height = re.match(r"высот[ау]\s+CH\s+равн[ао]\s*", rest)
        assignment = re.match(rf"({_QUANTITY})\s*=\s*", rest)
        if height:
            altitude, name, end = True, "CH", height.end()
        elif assignment:
            name, end = _key(assignment[1]), assignment.end()
        else:
            raise AltitudeSolveError("an unreviewed altitude statement remains")
        value, rest = _value(rest[end:])
        if name in values and _parse_positive_value(
            values[name]
        ) != _parse_positive_value(value):
            raise AltitudeSolveError("conflicting altitude givens")
        values[name] = value
    if len(values) != 2 or requested in values:
        raise AltitudeSolveError("two independent givens and a new target are required")
    formulas = []
    for name, value in values.items():
        label = (
            "\\" + name[:-1] + " " + name[-1]
            if name.endswith(("A", "B")) and len(name) > 2
            else name
        )
        formulas.append(
            f'<span data-inline-latex="{escape(label + "=" + value, quote=True)}"></span>'
        )
    label = (
        "\\" + requested[:-1] + " " + requested[-1] if len(requested) > 2 else requested
    )
    height = "CH — высота, " if altitude else ""
    return (
        "<p>В треугольнике ABC угол C равен 90°, "
        + height
        + ", ".join(formulas)
        + f'. Найдите <span data-inline-latex="{escape(label, quote=True)}"></span>.</p>'
    )
