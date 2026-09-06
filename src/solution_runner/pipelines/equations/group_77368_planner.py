"""Strict first-parent-solution repair planner for group 77368."""
from __future__ import annotations
from fractions import Fraction
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError
RULE = "elementary-equations-77368-equal-squares-first-solution"
PARENT_PROBLEM_ID = "9475eb24-58d3-44e6-83e3-42bea6d8d519"
_F = re.compile(r"\((?P<a1>[1-9]\d*)?x(?P<b>[+-][1-9]\d*)\)\^\{2\}=\((?P<a2>[1-9]\d*)?x(?P<c>[+-][1-9]\d*)\)\^\{2\}")
def build_repair_plan(context: dict[str,Any], *, parent_condition_asset_id: str|None, parent_solution_html: str="", current_asset_content_type: str|None=None)->RepairPlan:
    del parent_solution_html,current_asset_content_type
    if parent_condition_asset_id not in (None,""): raise RightTrianglePlanError("group 77368 must not have a condition asset")
    content=_normalized_content(context); condition=_section(content,"condition"); answer=_section(content,"answer"); solution=_section(content,"solution")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()): raise RightTrianglePlanError("condition is incomplete")
    soup=BeautifulSoup(str(condition.get("html") or ""),"html.parser"); spans=soup.find_all("span")
    if len(spans)!=1 or spans[0].get_text(strip=True): raise RightTrianglePlanError("equation markup is ambiguous")
    formula=str(spans[0].get("data-inline-latex") or ""); m=_F.fullmatch(formula)
    if not m: raise RightTrianglePlanError("condition does not match group 77368")
    a1, a2 = (int(m.group(k) or "1") for k in ("a1", "a2"))
    if a1 != a2: raise RightTrianglePlanError("linear coefficients differ")
    a,b,c = a1, int(m.group("b")), int(m.group("c")); root=Fraction(-(b+c),2*a)
    divisor = root.denominator
    while divisor % 2 == 0: divisor //= 2
    while divisor % 5 == 0: divisor //= 5
    if divisor != 1: raise RightTrianglePlanError("root has an infinite decimal representation")
    sign = "-" if root.numerator < 0 else ""
    numerator = abs(root.numerator); denominator = root.denominator; places = 0
    while denominator > 1:
        if denominator % 2 == 0: denominator //= 2
        else: denominator //= 5
        places += 1
    scaled = numerator * (10**places) // root.denominator
    digits = str(scaled).zfill(places + 1)
    root_text = sign + (digits if places == 0 else f"{digits[:-places]},{digits[-places:]}")
    left=f"{a*a}x^{{2}}{2*a*b:+d}x+{b*b}".replace("+-","-"); right=f"{a*a}x^{{2}}{2*a*c:+d}x+{c*c}".replace("+-","-")
    coef=2*a*(b-c); const=c*c-b*b; linear=f"{coef}x={const}".replace("+-","-")
    expected_condition=f'<p>Ре­ши­те урав­не­ние <span data-inline-latex="{formula}"></span>.</p>'
    expected_solution=('<p>Воз­ве­дем в квад­рат, ис­поль­зуя фор­му­лы квад­ра­та суммы и квад­ра­та раз­но­сти: '
        '<span data-inline-latex="(a\\pm b)^{2}=a^{2}\\pm (2ab)+b^{2}"></span>:</p><center><p><span> '
        f'<span data-inline-latex="{formula}\\iff {left}={right}\\iff {linear}\\iff x={root_text.replace(",","{,}")}"></span>.</span></p></center>')
    changes=[]
    if str(condition.get("html") or "")!=expected_condition: changes.append(_section_transformation(condition,"condition","Условие",expected_condition))
    if solution is None or str(solution.get("html") or "")!=expected_solution: changes.append(_section_transformation(solution,"solution","Решение",expected_solution))
    actual=BeautifulSoup(str(answer.get("html") or "") if answer else "","html.parser").get_text("",strip=True).replace(" ","")
    if actual!=root_text: changes.append(_section_transformation(answer,"answer","Ответ",f'<p><span data-effect="spaced">{root_text}</span></p>'))
    return RepairPlan(answer=root_text,transformations=tuple(changes))
