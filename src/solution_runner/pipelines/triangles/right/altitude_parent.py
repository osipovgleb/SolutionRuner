"""Prepare reviewed parent methods with the existing exact altitude inference."""

import gzip
import hashlib
import re
from dataclasses import replace
from fractions import Fraction
from importlib.resources import files

import sympy as sp
from bs4 import BeautifulSoup

from ...core.numbers import NumberFormatError, format_answer
from ...probability import solution_diagrams as diagrams
from ...probability.common import line
from ...word_problems.math_common import fraction
from .altitude_input import canonical_condition
from .altitude_methods import multiple_parent, tangent_solutions
from .altitude_solver import AltitudeSolveError, solve_altitude_condition
from .altitude_transcription import repair_condition

_SOURCES = {
    "a99e8a50-d3f3-4b22-ab0a-0a334b60e1fc": "a0a5d4eba1fdc72d87e26054f0ccda8e2f147504300529b86fd3d073713ccc94",
    "cc371621-44a0-459c-a9a9-d76931f0168f": "37a2be98a07658eafe13934081e7d18f41e9fdd88de7ca47717e38d9bb48b414",
    "122ba21d-0e6e-4fae-b049-960fdd911f3a": "b86cae6cecbfdbd824d174bd916aa6c866794972789f12ee0e6029579b6e8c04",
}
_EQUALITY_FIGURE = "cc371621-44a0-459c-a9a9-d76931f0168f"
_INTRO = "Углы A и HCB равны как углы со взаимно перпендикулярными сторонами."


def _opposite(name):
    lengths = {"AC": "BC", "BC": "AC", "AH": "BH", "BH": "AH"}
    if len(name) > 2 and name[-1] in "AB":
        return name[:-1] + ("B" if name[-1] == "A" else "A")
    return lengths.get(name, name)


def _source(source):
    if source not in _SOURCES:
        raise AltitudeSolveError("the altitude figure needs a mathematical audit")
    blob = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(blob).hexdigest() != _SOURCES[source]:
        raise AltitudeSolveError("the audited altitude figure has changed")
    return blob


def _method(expression):
    ratio = re.match(r"\\(sin|cos|tg)A=", expression)
    if ratio:
        function = ratio[1] + "A"
        numerator, denominator = {
            "sinA": ("BH", "BC"),
            "cosA": ("CH", "BC"),
            "tgA": ("BH", "CH"),
        }[function]
        if rf"\frac{{{numerator}}}{{{denominator}}}" not in expression:
            raise AltitudeSolveError(
                "the parent must use the corresponding BCH definition"
            )
        if r"\sqrt{BC^2-BH^2}" in expression:
            known = {"BC", "BH"}
        elif r"\sqrt{BC^2-CH^2}" in expression:
            known = {"BC", "CH"}
        elif r"\sqrt{CH^2+BH^2}" in expression or r"\sqrt{BH^2+CH^2}" in expression:
            known = {"CH", "BH"}
        else:
            known = {numerator, denominator}
        kind, requested = "ratio", function
    elif expression.startswith(r"CH=BC\cos"):
        kind, requested = "projection", "CH"
        known = {"BC", "sinA" if r"\sin^2A" in expression else "cosA"}
    elif expression.startswith(r"BH=BC\sin"):
        requested = "BH"
        if r"AC(1-\cos^2A)" in expression:
            kind, known = "ac_cos", {"AC", "cosA"}
        else:
            kind, known = (
                "projection",
                {"BC", "cosA" if r"\cos^2A" in expression else "sinA"},
            )
    elif expression.startswith("AB=") and r"\frac{AC^2}{AH}" in expression:
        kind, requested, known = "metric", "AB", {"AH", "cosA"}
    elif expression.startswith("AB=") and r"\frac{BH}{\sin^2A}" in expression:
        kind, requested, known = "double_sin", "AB", {"BH", "sinA"}
    elif expression.startswith("AH=") and r"\frac{BH}{\tg^2A}" in expression:
        kind, requested, known = "double_tg", "AH", {"BH", "tgA"}
    else:
        raise AltitudeSolveError("the complete parent method has not been reviewed")
    return kind, requested, known


def _parent(html):
    soup = BeautifulSoup(html, "html.parser")
    if len(soup.select('section[data-content-kind="solution"]')) > 1:
        return multiple_parent(soup)
    if soup.select('section[data-content-kind="solution"]'):
        raise AltitudeSolveError(
            "the structured parent requires its complete reviewed methods"
        )
    if re.search(
        r"(?:второй|третий)\s+способ|альтернативное|другое\s+решение",
        soup.get_text(" ", strip=True),
        re.IGNORECASE,
    ):
        raise AltitudeSolveError("every parent method must be reviewed")
    forms = soup.select("[data-inline-latex]")
    if len(forms) != 1:
        raise AltitudeSolveError("one reviewed parent formula chain is required")
    raw = forms[0]["data-inline-latex"]
    expression = "".join(raw.split()).replace(r"\operatorname{tg}", r"\tg")
    expression = (
        expression.replace(r"\left", "").replace(r"\right", "").replace("^{2}", "^2")
    )
    expression = expression.replace("CB", "BC").replace("HB", "BH")
    expression = expression.replace(r"\angleA", "A").replace("ACtgA", r"AC\tgA")
    kind, requested, known = _method(expression)
    images = soup.find_all("img")
    if images:
        prefix = str(soup).split(str(images[0]), 1)[0]
        if (
            len(images) != 1
            or kind != "double_tg"
            or images[0].get("data-asset-id") != _EQUALITY_FIGURE
            or re.sub(r"<[^>]*>", "", prefix).strip()
        ):
            raise AltitudeSolveError(
                "the parent figure placement has not been reviewed"
            )
    return (
        kind,
        requested,
        known,
        ("CB" in raw and "BC" not in raw),
        ("HB" in raw and "BH" not in raw),
        bool(images),
    )


def _display(solved):
    values = {key: sp.latex(number) for key, number in solved.values}
    values.update({key: latex for key, _, latex in solved.givens})
    return values


def _ratio_rows(solved, known):
    value = _display(solved)
    function = solved.requested[:-1]
    numerator, denominator = {
        "sin": ("BH", "BC"),
        "cos": ("CH", "BC"),
        "tg": ("BH", "CH"),
    }[function]
    needed = {numerator, denominator} - known
    rows = []
    if needed:
        missing = needed.pop()
        first, second = (
            ("CH", "BH")
            if missing == "BC"
            else ("BC", "CH" if missing == "BH" else "BH")
        )
        sign = "+" if missing == "BC" else "-"
        rows += [
            r"BC^2=CH^2+BH^2" if missing == "BC" else r"BC^2=BH^2+CH^2",
            rf"{missing}=\sqrt{{{first}^2{sign}{second}^2}}=\sqrt{{({value[first]})^2{sign}({value[second]})^2}}={value[missing]}",
        ]
    rows += [
        rf"\{function} A=\{function}\angle HCB=\frac{{{numerator}}}{{{denominator}}}=\frac{{{value[numerator]}}}{{{value[denominator]}}}"
    ]
    return rows


def _rows(kind, solved):
    raw = {k: tex for k, _, tex in solved.givens}
    value = _display(solved)
    if kind == "ratio":
        return _ratio_rows(solved, set(raw))
    if kind == "abc_cos":
        return [
            r"AB^2=AC^2+BC^2",
            rf"AB=\sqrt{{({value['AC']})^2+({value['BC']})^2}}={value['AB']}",
            r"\cos B="
            + fraction("BC", "AB")
            + "="
            + fraction(value["BC"], value["AB"]),
        ]
    if kind == "projection":
        target = solved.requested
        function = "cosA" if target == "CH" else "sinA"
        rows = [rf"{target}=BC\{function[:-1]}\angle HCB=BC\{function[:-1]} A"]
        if function not in raw:
            given = "sinA" if function == "cosA" else "cosA"
            rows += [
                rf"\{function[:-1]} A=\sqrt{{1-\{given[:-1]}^2 A}}=\sqrt{{1-({value[given]})^2}}={value[function]}"
            ]
        return rows + [rf"{target}=({value['BC']})\cdot({value[function]})"]
    if kind == "ac_cos":
        top = rf"({value['AC']})(1-({value['cosA']})^2)"
        return [
            r"BH=BC\sin\angle HCB=BC\sin A",
            r"BC=AC\tg A,\quad\tg A=" + fraction(r"\sin A", r"\cos A"),
            "BH="
            + fraction(r"AC\sin^2 A", r"\cos A")
            + "="
            + fraction(r"AC(1-\cos^2 A)", r"\cos A"),
            "BH=" + fraction(top, value["cosA"]),
        ]
    if kind == "metric":
        return [
            r"\cos A="
            + fraction("AH", "AC")
            + r"\Longrightarrow AC="
            + fraction("AH", r"\cos A")
            + "="
            + fraction(value["AH"], value["cosA"])
            + "="
            + value["AC"],
            r"AC^2=AB\cdot AH",
            "AB="
            + fraction("AC^2", "AH")
            + "="
            + fraction("(" + value["AC"] + ")^2", value["AH"]),
        ]
    function = "sin" if kind == "double_sin" else "tg"
    middle, first, requested = (
        ("BC", "BH", "AB") if kind == "double_sin" else ("CH", "BH", "AH")
    )
    name = "\\" + function + " A"
    return [
        name
        + "="
        + fraction(first, middle)
        + r"\Longrightarrow "
        + middle
        + "="
        + fraction(first, name)
        + "="
        + fraction(value[first], value[function + "A"])
        + "="
        + value[middle],
        name
        + "="
        + fraction(middle, requested)
        + r"\Longrightarrow "
        + requested
        + "="
        + fraction(middle, name)
        + "="
        + fraction(value[middle], value[function + "A"]),
    ]


def _figures(content, parent_asset_id, illustrated):
    _source(parent_asset_id)
    expected = {"image_1": parent_asset_id}
    if illustrated:
        expected["image_2"] = _EQUALITY_FIGURE
    assets = content.get("assets", [])
    if (
        not isinstance(assets, list)
        or any(
            not isinstance(a, dict)
            or expected.get(a.get("asset_key")) != a.get("asset_id")
            or a.get("kind") != "ordinary_image"
            or a.get("url") != "/assets/" + a["asset_id"]
            for a in assets
        )
        or sum(a.get("asset_key") == "image_1" for a in assets) != 1
        or len({a["asset_key"] for a in assets}) != len(assets)
    ):
        raise AltitudeSolveError(
            "the altitude figure metadata does not match the parent"
        )
    image, keys, changes = "", (), ()
    if illustrated:
        blob = _source(_EQUALITY_FIGURE)
        if any(a.get("asset_id") == _EQUALITY_FIGURE for a in assets):
            markup, key, changes = diagrams.image(
                content, "image_2", "", source_id=_EQUALITY_FIGURE
            )
        else:
            source = {
                "asset_key": "image_2",
                "source_asset_id": _EQUALITY_FIGURE,
                "url": "/assets/" + _EQUALITY_FIGURE,
                "sha256": _SOURCES[_EQUALITY_FIGURE],
            }
            markup, key, changes = diagrams.image(
                content, "image_2", "", svg=blob.decode(), generated=(source,)
            )
        image, keys = str(BeautifulSoup(markup, "html.parser").find("img")), (key,)
    return image, keys, changes


def _render(kind, solved, *, answer, mirrored, reversed_segments, image):
    if kind in {"hypotenuse_ah_methods", "hypotenuse_bh_methods"}:
        from .altitude_hypotenuse_methods import render

        return render(kind, _display(solved), answer)
    if kind == "complementary_height_methods":
        from .altitude_complement_methods import render

        return render(solved, _display(solved), answer)
    if kind == "height_tangent_methods":
        from .altitude_ratio_methods import render

        return render(solved, _display(solved), answer)
    if kind in {"projection_sinA_methods", "projection_cosA_methods"}:
        from .altitude_projection_methods import render

        return render(kind, _display(solved), answer)
    if kind == "tangent_bh_methods":
        return tangent_solutions(_display(solved), answer)
    reflected = (
        replace(
            solved,
            requested=_opposite(solved.requested),
            givens=tuple(
                (_opposite(key), number, latex) for key, number, latex in solved.givens
            ),
            values=tuple((_opposite(key), number) for key, number in solved.values),
        )
        if mirrored
        else solved
    )
    rows = _rows(kind, reflected)
    if mirrored:
        rows = [row.translate(str.maketrans({"A": "B", "B": "A"})) for row in rows]
    rows[-1] += "=" + answer.replace(",", "{,}")
    if reversed_segments[0]:
        rows = [
            row.replace("AC", "CA") if mirrored else row.replace("BC", "CB")
            for row in rows
        ]
    if reversed_segments[1]:
        rows = [
            row.replace("AH", "HA") if mirrored else row.replace("BH", "HB")
            for row in rows
        ]
    intro = (
        "По теореме Пифагора и определению косинуса в прямоугольном треугольнике ABC."
        if kind == "abc_cos"
        else _INTRO
    )
    if mirrored:
        intro = intro.replace("A и HCB", "B и HCA")
    html = (
        '<section data-content-kind="solution" data-solution-title="Решение"><p>'
        + image
        + intro
        + "</p>"
    )
    for index, row in enumerate(rows):
        if kind == "ratio" and len(rows) > 1 and index == 0:
            triangle = "ACH" if mirrored else "BCH"
            html += f"<p>Найдём неизвестную сторону по теореме Пифагора в треугольнике {triangle}:</p>"
        elif kind == "metric" and index == 1:
            html += "<p>Квадрат катета равен произведению гипотенузы и проекции катета на неё:</p>"
        elif kind in {"double_sin", "double_tg"}:
            triangle = "BCH" if index == 0 else "ABC" if kind == "double_sin" else "ACH"
            html += f"<p>По определению тригонометрической функции в прямоугольном треугольнике {triangle}:</p>"
        html += line(row)
    html += "</section>"
    return html


def prepare(context, *, parent_asset_id, parent_solution_html):
    from .planner import RepairPlan, _section

    kind, requested, known, reverse_bc, reverse_bh, illustrated = _parent(
        parent_solution_html
    )
    context, condition_changes = repair_condition(context, parent_asset_id)
    content = context["normalized_content"]
    condition = _section(content, "condition")
    canonical = canonical_condition(condition["html"], source=parent_asset_id)
    solved = solve_altitude_condition(canonical)
    givens = {key for key, _, _ in solved.givens}
    mirrored = (
        kind == "ratio"
        and solved.requested == _opposite(requested)
        and givens == {_opposite(key) for key in known}
    )
    if not mirrored and (
        requested == "cosA"
        and kind == "ratio"
        and solved.requested == "cosB"
        and givens == {"AC", "BC"}
    ):
        kind = "abc_cos"
    elif not mirrored and (solved.requested != requested or givens != known):
        raise AltitudeSolveError("the child requires a different parent method")
    if solved.exact_value.is_Rational is not True:
        raise AltitudeSolveError("an exact finite decimal answer is required")
    try:
        answer = format_answer(
            Fraction(int(solved.exact_value.p), int(solved.exact_value.q))
        )
    except NumberFormatError as exc:
        raise AltitudeSolveError("an exact finite decimal answer is required") from exc
    image, keys, changes = _figures(content, parent_asset_id, illustrated)
    html = _render(
        kind,
        solved,
        answer=answer,
        mirrored=mirrored,
        reversed_segments=(reverse_bc, reverse_bh),
        image=image,
    )
    plan = diagrams.repair(
        condition,
        _section(content, "answer"),
        _section(content, "solution"),
        answer,
        html,
        keys,
        changes,
    )
    return RepairPlan(plan.answer, condition_changes + plan.transformations)
