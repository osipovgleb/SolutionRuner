"""Evaluate a target equal to the sum of two given linear expressions."""
from __future__ import annotations
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content,_section,_section_transformation
from ..triangles.right.planner import RepairPlan,RightTrianglePlanError
_TARGET=re.compile(r"^(?P<x>\d*)x\+(?P<y>\d*)y\+(?P<z>\d*)z$")
_FIRST=re.compile(r"^(?P<x>\d*)x\+(?P<y>\d*)y=(?P<v>-?\d+)$")
_SECOND=re.compile(r"^(?P<z>\d*)z\+(?P<y>\d*)y=(?P<v>-?\d+)$")
def n(v): return int(v or '1')
def build_context_repair_plan(context:dict[str,Any])->RepairPlan:
 content=_normalized_content(context); c=_section(content,'condition')
 if c is None or content.get('assets') or tuple(c.get('asset_keys') or ()): raise RightTrianglePlanError('condition must be text-only')
 s=BeautifulSoup(str(c.get('html') or ''),'html.parser'); fs=[str(q.get('data-inline-latex') or '').replace(' ','') for q in s.find_all('span',attrs={'data-inline-latex':True})]
 if len(fs)!=3: raise RightTrianglePlanError('condition must contain target and two equations')
 t,a,b=_TARGET.fullmatch(fs[0]),_FIRST.fullmatch(fs[1]),_SECOND.fullmatch(fs[2])
 if not t or not a or not b: raise RightTrianglePlanError('condition does not contain matching expressions')
 sums=(n(a['x']), n(a['y'])+n(b['y']), n(b['z'])); target=(n(t['x']),n(t['y']),n(t['z']))
 if any(total % wanted for total,wanted in zip(sums,target)) or len({total // wanted for total,wanted in zip(sums,target)}) != 1: raise RightTrianglePlanError('target is not proportional to the sum of given expressions')
 multiplier=sums[0]//target[0]; total=int(a['v'])+int(b['v'])
 answer=total//multiplier
 summed=f"({fs[1].split('=')[0]})+({fs[2].split('=')[0]})={a['v']}+{b['v']}={total}"
 primary=f"{multiplier}({fs[0]})={total}\\iff {fs[0]}={answer}" if multiplier != 1 else f"{fs[0]}={total}"
 html=f'<p>Из условия можно заметить: после сложения двух уравнений левая часть получается пропорциональной искомому выражению.</p><center><p><span data-inline-latex="{summed}"></span>.</p></center><p>Сравним полученную левую часть с искомым выражением:</p><center><p><span data-inline-latex="{primary}"></span>.</p></center>'
 ans=_section(content,'answer'); sol=_section(content,'solution'); changes=[]
 if sol is None or str(sol.get('html') or '')!=html: changes.append(_section_transformation(sol,'solution','Решение',html))
 now=BeautifulSoup(str(ans.get('html') or '') if ans else '','html.parser').get_text('',strip=True).replace(' ','')
 if now!=str(answer): changes.append(_section_transformation(ans,'answer','Ответ',f'<p><span data-effect="spaced">{answer}</span></p>'))
 return RepairPlan(answer=str(answer),transformations=tuple(changes))
