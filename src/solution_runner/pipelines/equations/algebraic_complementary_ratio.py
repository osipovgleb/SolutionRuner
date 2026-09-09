"""Plans for p(x)+p(A-x) where the two values cancel."""
from __future__ import annotations
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError

_DEF=re.compile(r"^p\(x\)=\\frac\{x\((?P<a>-?\d+)-x\)\}\{x(?P<s>[+-])(?P<h>\d+)\}$")

def build_context_repair_plan(context: dict[str,Any])->RepairPlan:
 c=_normalized_content(context); q=_section(c,"condition")
 if q is None or c.get("assets"): raise RightTrianglePlanError("text-only condition required")
 soup=BeautifulSoup(str(q.get("html") or ""),"html.parser"); fs=[str(n.get("data-inline-latex") or "").replace(" ","") for n in soup.find_all("span",attrs={"data-inline-latex":True})]
 m=next((_DEF.fullmatch(f) for f in fs if f.startswith("p(x)=")),None)
 if not m: raise RightTrianglePlanError("condition does not match complementary ratio")
 a=int(m["a"]); h=int(m["h"]); sign=m["s"]
 if a != (2*h if sign=="-" else -2*h): raise RightTrianglePlanError("denominator is not the midpoint")
 other=f"{a}-x" if a>=0 else f"{a}-x"
 p1=f"p(x)=\\frac{{x({a}-x)}}{{x{sign}{h}}}"
 middle_denominator = f"{h}-x" if a > 0 else f"-{h}-x"
 p2=(f"p({other})=\\frac{{({a}-x)({a}-({a}-x))}}{{({a}-x){sign}{h}}}="
     f"\\frac{{({a}-x)({a}-{a}+x)}}{{{a}-x{sign}{h}}}="
     f"\\frac{{({a}-x)x}}{{{middle_denominator}}}="
     f"\\frac{{({a}-x)x}}{{-(x{sign}{h})}}=-\\frac{{x({a}-x)}}{{x{sign}{h}}}")
 main=f"p(x)+p({other})=\\frac{{x({a}-x)}}{{x{sign}{h}}}-\\frac{{x({a}-x)}}{{x{sign}{h}}}=0"
 value=(h+1 if a>0 else -h+1)
 other_value=a-value
 alt=(f"p({value})+p({other_value})="
      f"\\frac{{{value}({a}-{value})}}{{{value}{sign}{h}}}+"
      f"\\frac{{{other_value}({a}-{other_value})}}{{{other_value}{sign}{h}}}=0")
 html=(f'<p>Вычислим значения функции:</p><center><p><span data-inline-latex="{p1}"></span>.</p></center><center><p><span data-inline-latex="{p2}"></span>.</p></center><p>Сложим полученные значения:</p><center><p><span data-inline-latex="{main}"></span>.</p></center><p><b>Приведем другое решение</b></p><p>Так как это задание первой части, переменной <span data-inline-latex="x"></span> в ответе быть не может, значит, она должна сократиться. Подставим, например, {value} вместо переменной:</p><center><p><span data-inline-latex="{alt}"></span>.</p></center>')
 ans=_section(c,"answer"); sol=_section(c,"solution"); changes=[]
 if sol is None or str(sol.get("html") or "")!=html: changes.append(_section_transformation(sol,"solution","Решение",html))
 if BeautifulSoup(str(ans.get("html") or "") if ans else "","html.parser").get_text("",strip=True)!="0": changes.append(_section_transformation(ans,"answer","Ответ",'<p><span data-effect="spaced">0</span></p>'))
 return RepairPlan(answer="0",transformations=tuple(changes))
