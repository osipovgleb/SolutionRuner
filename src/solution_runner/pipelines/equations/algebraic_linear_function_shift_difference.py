"""Evaluate q(b-h)-q(b+h) for q(b)=kb."""
from __future__ import annotations
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content,_section,_section_transformation
from ..triangles.right.planner import RepairPlan,RightTrianglePlanError
_TARGET=re.compile(r"^q\(b-(?P<h>\d+)\)-q\(b\+(?P=h)\)$")
_FUNCTION=re.compile(r"^q\(b\)=(?P<k>-?\d*)b$")
def build_context_repair_plan(context:dict[str,Any])->RepairPlan:
 c=_normalized_content(context); condition=_section(c,'condition')
 if condition is None or c.get('assets') or tuple(condition.get('asset_keys') or ()): raise RightTrianglePlanError('condition must be text-only')
 s=BeautifulSoup(str(condition.get('html') or ''),'html.parser'); f=[str(x.get('data-inline-latex') or '').replace(' ','') for x in s.find_all('span',attrs={'data-inline-latex':True})]
 if len(f)!=2: raise RightTrianglePlanError('condition must contain target and function')
 t,g=_TARGET.fullmatch(f[0]),_FUNCTION.fullmatch(f[1])
 if not t or not g: raise RightTrianglePlanError('condition does not match shifted linear function')
 h=int(t['h']); k=int(g['k'] or '1'); answer=-2*k*h
 main=f"{f[0]}={k}(b-{h})-{k}(b+{h})={k}b{(-k*h):+d}-{k}b{(-k*h):+d}={answer}".replace('+-','-')
 left,right=1-h,1+h; qleft,qright=k*left,k*right
 html=f'<p>Подставим аргументы в формулу функции:</p><center><p><span data-inline-latex="{main}"></span>.</p></center><p><b>Приведём другое решение</b></p><p>Так как это задание первой части, переменная <span data-inline-latex="b"></span> в ответе быть не может, значит, она должна сократиться.</p><p>Подставим <span data-inline-latex="b=1"></span> в искомое выражение:</p><center><p><span data-inline-latex="q({left})-q({right})"></span>.</p></center><p>Найдём значения функции:</p><center><p><span data-inline-latex="q({left})={k}\\cdot({left})={qleft},\\quad q({right})={k}\\cdot({right})={qright}"></span>.</p></center><p>Подставим найденные значения:</p><center><p><span data-inline-latex="{qleft}-({qright})={answer}"></span>.</p></center>'
 ans=_section(c,'answer'); sol=_section(c,'solution'); changes=[]
 if sol is None or str(sol.get('html') or '')!=html: changes.append(_section_transformation(sol,'solution','Решение',html))
 now=BeautifulSoup(str(ans.get('html') or '') if ans else '','html.parser').get_text('',strip=True).replace(' ','')
 if now!=str(answer): changes.append(_section_transformation(ans,'answer','Ответ',f'<p><span data-effect="spaced">{answer}</span></p>'))
 return RepairPlan(answer=str(answer),transformations=tuple(changes))
