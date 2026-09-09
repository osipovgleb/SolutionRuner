"""Plans for ratios of equivalent monomials written in different orders."""
from __future__ import annotations
from fractions import Fraction
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError

_FRACTION = re.compile(r"^\\frac\{(?P<a>\d*)(?P<m1>[axy]{3})-\(-(?P<b>\d*)(?P<m2>[axy]{3})\)\}\{(?P<c>\d*)(?P<m3>[axy]{3})\}$")
_COLON = re.compile(r"^\((?P<a>\d*)(?P<m1>[axy]{3})-\(-(?P<b>\d*)(?P<m2>[axy]{3})\)\)\\colon(?P<c>\d*)(?P<m3>[axy]{3})$")

def _formula(condition: dict[str, Any]) -> str:
    soup=BeautifulSoup(str(condition.get("html") or ""),"html.parser")
    items=soup.find_all("span",attrs={"data-inline-latex":True})
    if len(items)!=1: raise RightTrianglePlanError("condition must contain one formula")
    return str(items[0].get("data-inline-latex") or "").replace(" ","")

def _latex(value: Fraction) -> str:
    return str(value.numerator) if value.denominator==1 else f"{'-' if value<0 else ''}\\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"

def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content=_normalized_content(context); condition=_section(content,"condition")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()): raise RightTrianglePlanError("monomial-ratio condition must be text-only")
    formula=_formula(condition); match=_FRACTION.fullmatch(formula) or _COLON.fullmatch(formula)
    if match is None or len({"".join(sorted(match[n])) for n in ("m1","m2","m3")}) != 1: raise RightTrianglePlanError("condition does not match a registered monomial ratio")
    a,b,c=(int(match[n] or "1") for n in ("a","b","c")); monomial="".join(sorted(match["m1"])); answer=_latex(Fraction(a+b,c))
    fraction=f"\\frac{{{a}{match['m1']}-(-{b}{match['m2']})}}{{{c}{match['m3']}}}"
    primary=f"{fraction}=\\frac{{{a}{monomial}+{b}{monomial}}}{{{c}{monomial}}}=\\frac{{{a+b}{monomial}}}{{{c}{monomial}}}={answer}"
    html=f'<center><p><span data-inline-latex="{primary}"></span>.</p></center>'
    answer_section=_section(content,"answer"); solution_section=_section(content,"solution"); changes=[]
    if solution_section is None or str(solution_section.get("html") or "") != html: changes.append(_section_transformation(solution_section,"solution","Решение",html))
    current=BeautifulSoup(str(answer_section.get("html") or "") if answer_section else "","html.parser").get_text("",strip=True).replace(" ","")
    if current != answer: changes.append(_section_transformation(answer_section,"answer","Ответ",f'<p><span data-effect="spaced">{answer}</span></p>'))
    return RepairPlan(answer=answer,transformations=tuple(changes))
