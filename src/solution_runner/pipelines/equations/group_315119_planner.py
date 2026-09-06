"""Equal-unit-fractions planner for group 315119."""
from __future__ import annotations
from fractions import Fraction
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content,_section,_section_transformation
from ..triangles.right.planner import RepairPlan,RightTrianglePlanError
RULE='elementary-equations-315119-equal-unit-fractions'
_F=re.compile(r'\\frac\{1\}\{(?P<a>-?\d*)x(?P<s>[+-])(?P<b>\d+)\}=\\frac\{1\}\{(?P<c>-?\d*)x(?P<t>[+-])(?P<d>\d+)\}')
def build_repair_plan(context:dict[str,Any],*,parent_condition_asset_id:str|None,parent_solution_html:str='',current_asset_content_type:str|None=None)->RepairPlan:
 del parent_solution_html,current_asset_content_type
 if parent_condition_asset_id not in (None,''):raise RightTrianglePlanError('group 315119 must not have assets')
 x=_normalized_content(context);q=_section(x,'condition');ans=_section(x,'answer');sol=_section(x,'solution')
 if q is None or x.get('assets') or tuple(q.get('asset_keys') or ()):raise RightTrianglePlanError('condition incomplete')
 soup=BeautifulSoup(str(q.get('html') or ''),'html.parser');sp=soup.find_all('span')
 if len(sp)!=1 or sp[0].get_text(strip=True):raise RightTrianglePlanError('condition ambiguous')
 f=str(sp[0].get('data-inline-latex') or '');m=_F.fullmatch(f)
 if not m:raise RightTrianglePlanError('condition does not match group 315119')
 a=int(m['a'] or '1');b=int(m['b']) if m['s']=='+' else -int(m['b']);c=int(m['c'] or '1');d=int(m['d']) if m['t']=='+' else -int(m['d'])
 if a==c:raise RightTrianglePlanError('equal denominators')
 root=Fraction(d-b,a-c);excluded=Fraction(-d,c)
 if root==Fraction(-b,a) or root==excluded:raise RightTrianglePlanError('root violates domain')
 def n(v):return str(v.numerator) if v.denominator==1 else f'\\frac{{{v.numerator}}}{{{v.denominator}}}'
 def lin(k,s,z):return ('' if k==1 else '-' if k==-1 else str(k))+'x'+s+str(abs(z))
 left=lin(a,m['s'],b);right=lin(c,m['t'],d);out=n(root)
 h='<p>Если две дроби с рав­ны­ми чис­ли­те­ля­ми равны, то равны их зна­ме­на­те­ли. Имеем:</p>'+f'<center><p><span data-inline-latex="{f}\\iff \\begin{{cases}}{left}={right}\\\\{right}\\ne0\\end{{cases}}\\iff \\begin{{cases}}x={out}\\\\x\\ne{n(excluded)}\\end{{cases}}\\iff x={out}"></span>.</p></center>'
 ch=[]
 if sol is None or sol.get('html')!=h:ch.append(_section_transformation(sol,'solution','Решение',h))
 cur=BeautifulSoup(str(ans.get('html') if ans else ''),'html.parser').get_text('',strip=True).replace(' ','')
 if cur!=out:ch.append(_section_transformation(ans,'answer','Ответ',f'<p><span data-effect="spaced">{out}</span></p>'))
 return RepairPlan(answer=out,transformations=tuple(ch))
