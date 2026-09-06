from __future__ import annotations
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content,_section,_section_transformation
from ..triangles.right.planner import RepairPlan,RightTrianglePlanError
RULE='elementary-equations-77370-expanded-square-linear'
R=re.compile(r'x\^\{2\}(?P<c>[+-][1-9]\d*)=\(x(?P<d>[+-][1-9]\d*)\)\^\{2\}')
def build_repair_plan(context:dict[str,Any],*,parent_condition_asset_id:str|None,parent_solution_html:str='',current_asset_content_type:str|None=None)->RepairPlan:
 del parent_solution_html,current_asset_content_type
 if parent_condition_asset_id not in (None,''): raise RightTrianglePlanError('assets unsupported')
 c=_normalized_content(context); q=_section(c,'condition'); a=_section(c,'answer'); s=_section(c,'solution'); sp=BeautifulSoup(str(q.get('html') if q else ''),'html.parser').find_all('span')
 if not q or c.get('assets') or len(sp)!=1: raise RightTrianglePlanError('condition unsupported')
 f=str(sp[0].get('data-inline-latex') or ''); m=R.fullmatch(f)
 if not m: raise RightTrianglePlanError('condition unsupported')
 cv,d=int(m['c']),int(m['d']); num=cv-d*d; den=2*d
 if num%den: raise RightTrianglePlanError('root unsupported')
 x=num//den; sol=f'<p>Вос­поль­зу­ем­ся фор­му­лой <span data-inline-latex="(a+b)^{{2}}=a^{{2}}+2ab+b^{{2}}"></span>:</p><center><p><span data-inline-latex="{f}\\iff x^{{2}}{cv:+d}=x^{{2}}{2*d:+d}x+{d*d}\\iff {2*d}x={num}\\iff x={x}"></span>.</p></center>'.replace('+-','-')
 out=str(x); ch=[]
 if s is None or str(s.get('html') or '')!=sol: ch.append(_section_transformation(s,'solution','Решение',sol))
 if BeautifulSoup(str(a.get('html') if a else ''),'html.parser').get_text('',strip=True)!=out: ch.append(_section_transformation(a,'answer','Ответ',f'<p><span data-effect="spaced">{out}</span></p>'))
 return RepairPlan(answer=out,transformations=tuple(ch))
