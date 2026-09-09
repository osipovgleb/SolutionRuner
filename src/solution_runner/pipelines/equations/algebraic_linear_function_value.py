"""Evaluate a cancelling linear expression containing p(a)."""
from __future__ import annotations
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content,_section,_section_transformation
from ..triangles.right.planner import RepairPlan,RightTrianglePlanError
_TARGET=re.compile(r"^(?P<c>\d+)p\(a\)(?P<linear>[+-]\d*)a(?P<const>[+-]\d+)$")
_FUNCTION=re.compile(r"^p\(a\)=(?P<m>\d*)a(?P<b>[+-]\d+)$")
def _n(v): return (1 if v=="+" else -1 if v=="-" else int(v.replace("+","")))
def _forms(condition):
 s=BeautifulSoup(str(condition.get("html") or ""),"html.parser"); f=[str(x.get("data-inline-latex") or "").replace(" ","") for x in s.find_all("span",attrs={"data-inline-latex":True})]
 if len(f)!=2: raise RightTrianglePlanError("condition must contain expression and p(a)")
 return f
def build_context_repair_plan(context:dict[str,Any])->RepairPlan:
 content=_normalized_content(context); cond=_section(content,"condition")
 if cond is None or content.get("assets") or tuple(cond.get("asset_keys") or ()): raise RightTrianglePlanError("linear function condition must be text-only")
 target,function=_forms(cond); t,f=_TARGET.fullmatch(target),_FUNCTION.fullmatch(function)
 if not t or not f: raise RightTrianglePlanError("condition does not match a registered linear function value")
 c=int(t['c']); linear,constant,m,b=_n(t['linear']),_n(t['const']),int(f['m'] or '1'),_n(f['b'])
 if linear != -c*m: raise RightTrianglePlanError("a terms do not cancel")
 answer=c*b+constant; primary=f"{target}={c}({m}a{f['b']}){t['linear']}a{t['const']}={c*m}a{c*b:+d}{t['linear']}a{t['const']}={answer}".replace('+-','-')
 p1=m+b
 at_one=f"{c}p(1){linear:+d}\\cdot1{constant:+d}".replace('+-','-')
 p_one=f"p(1)={m}\\cdot1{f['b']}={p1}"
 final=f"{c}\\cdot({p1}){linear:+d}\\cdot1{constant:+d}={answer}".replace('+-','-')
 html=f'<p>Подставим выражение для <span data-inline-latex="p(a)"></span>:</p><center><p><span data-inline-latex="{primary}"></span>.</p></center><p><b>Приведём другое решение</b></p><p>Так как это задание первой части, переменная <span data-inline-latex="a"></span> в ответе быть не может, значит, она должна сократиться.</p><p>Подставим <span data-inline-latex="a=1"></span> в искомое выражение:</p><center><p><span data-inline-latex="{at_one}"></span>.</p></center><p>Найдём <span data-inline-latex="p(1)"></span>:</p><center><p><span data-inline-latex="{p_one}"></span>.</p></center><p>Подставим найденное значение:</p><center><p><span data-inline-latex="{final}"></span>.</p></center>'
 ans=_section(content,'answer'); sol=_section(content,'solution'); changes=[]
 if sol is None or str(sol.get('html') or '')!=html: changes.append(_section_transformation(sol,'solution','Решение',html))
 cur=BeautifulSoup(str(ans.get('html') or '') if ans else '', 'html.parser').get_text('',strip=True).replace(' ','')
 if cur!=str(answer): changes.append(_section_transformation(ans,'answer','Ответ',f'<p><span data-effect="spaced">{answer}</span></p>'))
 return RepairPlan(answer=str(answer),transformations=tuple(changes))
