"""Strict elementary angle/area rules for the ten audited general-triangle groups."""
from fractions import Fraction
import re
from typing import Any
from bs4 import BeautifulSoup

from ..isosceles.planner import _asset_transformation, _normalized_content, _section, _section_transformation
from ..right.planner import RepairPlan, RightTrianglePlanError

RULES = {
    "general-triangle-27592-midline-area": (r"площадь треугольника ABC равна\s*([0-9]+).*площадь треугольника CDE", lambda m: Fraction(int(m.group(1)), 4), "S_{CDE}=S_{ABC}/4"),
    "general-triangle-27623-altitude-area-ratio": (r"сторонами\s*([0-9]+)\s*и\s*([0-9]+).*перв\w*\s+сторон\w*,?\s+равна\s*([0-9]+).*втор\w*\s+сторон\w*", lambda m: Fraction(int(m.group(1))*int(m.group(3)), int(m.group(2))), "h_2=h_1a_1/a_2"),
    "general-triangle-27743-exterior-angle": (r"угол A равен\s*([0-9]+).*внешний угол.*B равен\s*([0-9]+).*угол C", lambda m: int(m.group(2))-int(m.group(1)), "C=B_{ext}-A"),
    "general-triangle-27757-altitude-angle": (r"угол A равен\s*([0-9]+).*угол BCH равен\s*([0-9]+).*угол ACB", lambda m: 90-int(m.group(1))-int(m.group(2)), "ACB=90-A-BCH"),
    "general-triangle-27758-bisector-angle": (r"угол C равен\s*([0-9]+).*угол CAD равен\s*([0-9]+).*угол B", lambda m: 180-2*int(m.group(2))-int(m.group(1)), "B=180-2CAD-C"),
    "general-triangle-27759-bisector-exterior-angle": (r"угол C равен\s*([0-9]+).*угол BAD равен\s*([0-9]+).*угол ADB", lambda m: int(m.group(1))+int(m.group(2)), "ADB=C+BAD"),
    "general-triangle-27762-orthocenter-angle": (r"угол A равен\s*([0-9]+).*угол DOE", lambda m: 180-int(m.group(1)), "DOE=180-A"),
    "general-triangle-27763-altitudes-angle-sum": (r"угла.*равны\s*([0-9]+).*и\s*([0-9]+).*тупой угол", lambda m: int(m.group(1))+int(m.group(2)), "D=α+β"),
    "general-triangle-27764-incenter-angle": (r"угол C равен\s*([0-9]+).*угол AOB", lambda m: Fraction(180+int(m.group(1)), 2), "AOB=90+C/2"),
    "general-triangle-27767-altitude-bisector-intersection": (r"угол BAD равен\s*([0-9]+).*угол AOC", lambda m: 90+int(m.group(1)), "AOC=90+BAD"),
}

def _replace_latex(parent_html: str, formulas: tuple[str, ...]) -> str:
    iterator = iter(formulas)
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        try:
            formula = next(iterator)
        except StopIteration:
            return match.group(0)
        count += 1
        return f'data-inline-latex="{formula}"'

    rendered = re.sub(r'data-inline-latex="[^"]*"', replace, parent_html)
    if count != len(formulas):
        raise RightTrianglePlanError("parent solution formula count drifted")
    return rendered


def _parent_solution(parent_html: str, rule: str, values: tuple[int, ...], value: Fraction | int) -> str:
    """Keep the parent's prose/markup and change only its value-bearing formula."""
    if not parent_html.strip():
        return ""
    if rule == "general-triangle-27592-midline-area":
        child_area = values[0] if values else None
        # The parent template ends with \cdot <area>=<answer>; preserve every other token.
        if child_area is not None:
            rendered = re.sub(r"(\\cdot\s*)\d+(\s*=\s*)\d+", rf"\g<1>{child_area}\g<2>{value}", parent_html, count=1)
            # Parent text contains soft hyphens and sometimes a narrow no-break space.
            return re.sub(r"\s+(?=Пло\u00ad*ща\u00ad*ди\u00ad*\s+по)", "</p><p>", rendered, count=1)
    if rule == "general-triangle-27623-altitude-area-ratio":
        rendered = parent_html
        if len(values) >= 3:
            formulas = (
                r"S_{ABC}=\frac{1}{2}CH\cdot AB=\frac{1}{2}AK\cdot CB",
                rf"\frac{{1}}{{2}}CH\cdot AB=\frac{{1}}{{2}}AK\cdot CB\iff AK=\frac{{CH\cdot AB}}{{CB}}\iff AK=\frac{{{values[2]}\cdot {values[0]}}}{{{values[1]}}}\iff AK={value}",
            )
            rendered = _replace_latex(rendered, formulas)
        return re.sub(r"\s+(?=Сле\u00ad*до\u00ad*ва\u00ad*тель\u00ad*но\s*,)", "</p><p>", rendered, count=1)
    if rule == "general-triangle-27743-exterior-angle" and len(values) >= 2:
        return _replace_latex(parent_html, (rf"\angle C=\angle B_{{\mathrm{{внешн}}}}-\angle A={values[1]}^{{\circ}}-{values[0]}^{{\circ}}={value}^{{\circ}}",))
    if rule == "general-triangle-27757-altitude-angle" and len(values) >= 2:
        return _replace_latex(parent_html, (rf"\angle ACB=\angle ACH-\angle BCH=(90^{{\circ}}-\angle A)-\angle BCH=90^{{\circ}}-{values[0]}^{{\circ}}-{values[1]}^{{\circ}}={value}^{{\circ}}",))
    if rule == "general-triangle-27758-bisector-angle" and len(values) >= 2:
        return _replace_latex(parent_html, (rf"\angle B=180^{{\circ}}-\angle A-\angle C=180^{{\circ}}-2\angle CAD-\angle C=180^{{\circ}}-2\cdot {values[1]}^{{\circ}}-{values[0]}^{{\circ}}={value}^{{\circ}}",))
    if rule == "general-triangle-27759-bisector-exterior-angle" and len(values) >= 2:
        return _replace_latex(parent_html, (
            rf"\angle CAD=\angle BAD={values[1]}^{{\circ}}",
            rf"\angle ADB=\angle CAD+\angle ACD={value}^{{\circ}}",
        ))
    if rule == "general-triangle-27762-orthocenter-angle" and values:
        return _replace_latex(parent_html, (rf"\angle DOE=360^{{\circ}}-\angle ADO-\angle OEA-\angle A=360^{{\circ}}-90^{{\circ}}-90^{{\circ}}-{values[0]}^{{\circ}}={value}^{{\circ}}",))
    if rule == "general-triangle-27763-altitudes-angle-sum" and len(values) >= 2:
        return _replace_latex(parent_html, (
            rf"\angle DOE=360^{{\circ}}-\angle CDO-\angle CEO-\angle C=360^{{\circ}}-90^{{\circ}}-90^{{\circ}}-(180^{{\circ}}-{values[0]}^{{\circ}}-{values[1]}^{{\circ}})={value}^{{\circ}}",
            rf"{values[0]}^{{\circ}}+{values[1]}^{{\circ}}={value}^{{\circ}}",
        ))
    if rule == "general-triangle-27764-incenter-angle" and values:
        half = Fraction(180 - values[0], 2)
        half_text = str(half.numerator) if half.denominator == 1 else f"\\frac{{{half.numerator}}}{{{half.denominator}}}"
        return _replace_latex(parent_html, (rf"\angle AOB=180^{{\circ}}-(\angle OAB+\angle OBA)=180^{{\circ}}-\frac{{1}}{{2}}(\angle A+\angle B)=180^{{\circ}}-\frac{{1}}{{2}}(180^{{\circ}}-\angle C)=180^{{\circ}}-\frac{{1}}{{2}}(180^{{\circ}}-{values[0]}^{{\circ}})=180^{{\circ}}-{half_text}^{{\circ}}={value}^{{\circ}}",))
    if rule == "general-triangle-27767-altitude-bisector-intersection" and values:
        return _replace_latex(parent_html, (rf"{values[0]}^{{\circ}}+90^{{\circ}}={value}^{{\circ}}",))
    raise RightTrianglePlanError("parent template substitution is not implemented for this rule")


def build_repair_plan(
    context: dict[str, Any], *, rule: str, parent_solution_html: str = "", parent_condition_asset_id: str = ""
) -> RepairPlan:
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    soup = BeautifulSoup(condition_html, "html.parser")
    # Put LaTeX attributes back into the visible stream at their exact position.
    for formula in soup.find_all(attrs={"data-inline-latex": True}):
        formula.replace_with(str(formula.get("data-inline-latex") or ""))
    text = " ".join(soup.get_text().replace("\u00ad", "").replace("\\", "").split())
    condition_values = tuple(int(x) for x in re.findall(r"\d+", text))
    spec = RULES.get(rule)
    if spec is None:
        raise RightTrianglePlanError("unsupported general-triangle rule")
    match = re.search(spec[0], text, re.I)
    if match is None:
        nums = [int(x) for x in re.findall(r"\d+", text)]
        if rule == "general-triangle-27743-exterior-angle" and len(nums) >= 2: value = nums[1] - nums[0]
        elif rule == "general-triangle-27757-altitude-angle" and len(nums) >= 2: value = 90 - nums[0] - nums[1]
        elif rule == "general-triangle-27758-bisector-angle" and len(nums) >= 2: value = 180 - 2 * nums[1] - nums[0]
        elif rule == "general-triangle-27759-bisector-exterior-angle" and len(nums) >= 2: value = nums[0] + nums[1]
        elif rule == "general-triangle-27762-orthocenter-angle" and nums: value = 180 - nums[0]
        elif rule == "general-triangle-27763-altitudes-angle-sum" and len(nums) >= 2: value = nums[0] + nums[1]
        elif rule == "general-triangle-27764-incenter-angle" and nums: value = Fraction(180 + nums[0], 2)
        elif rule == "general-triangle-27767-altitude-bisector-intersection" and nums: value = 90 + nums[0]
        else: raise RightTrianglePlanError("condition does not match registered rule")
    else:
        value = spec[1](match)
    if isinstance(value, Fraction) and value.denominator == 1:
        answer = str(value.numerator)
    elif isinstance(value, Fraction):
        answer = f"{value.numerator/value.denominator:g}".replace(".", ",")
    else:
        answer = str(value)
    answer_section = _section(content, "answer")
    current = BeautifulSoup(str(answer_section.get("html") or "") if answer_section else "", "html.parser").get_text().strip().replace(",", ".")
    changes: list[dict[str, Any]] = []
    try:
        if Fraction(current) != Fraction(value):
            changes.append(_section_transformation(answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'))
    except (ValueError, ZeroDivisionError):
        changes.append(_section_transformation(answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'))
    solution = _section(content, "solution")
    html = _parent_solution(parent_solution_html, rule, condition_values, value)
    if not html:
        html = f'<p>Используем свойство геометрии: <span data-inline-latex="{spec[2]}"></span>.</p><center><p><span data-inline-latex="ответ={answer}"></span>.</p></center>'
    current_solution = str(solution.get("html") or "") if solution else ""
    if solution is None or current_solution != html:
        changes.append(_section_transformation(solution, "solution", "Решение", html))
    condition_has_image = (
        "image_1" in tuple(str(key) for key in condition.get("asset_keys", []))
        or BeautifulSoup(condition_html, "html.parser").find("img", attrs={"data-asset-key": "image_1"}) is not None
    )
    if parent_condition_asset_id and not condition_has_image:
        changes.append(_asset_transformation(parent_condition_asset_id))
    return RepairPlan(answer=answer, transformations=tuple(changes))
