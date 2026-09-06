from __future__ import annotations
from fractions import Fraction
import math,re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content,_section,_section_transformation
from ..triangles.right.planner import RepairPlan,RightTrianglePlanError
RULE='elementary-equations-77371-fractional-square-root'
_R=re.compile(r'\\frac\{(?P<a>[1-9]\d*)\}\{(?P<b>[1-9]\d*)\}x\^\{2\}=(?:(?P<m>[1-9]\d*)\\frac\{(?P<p>[1-9]\d*)\}\{(?P<q>[1-9]\d*)\}|\\frac\{(?P<n>[1-9]\d*)\}\{(?P<d>[1-9]\d*)\})')
def build_repair_plan(context:dict[str,Any],*,parent_condition_asset_id:str|None,parent_solution_html:str='',current_asset_content_type:str|None=None)->RepairPlan:
 del parent_solution_html,current_asset_content_type
 if parent_condition_asset_id not in (None,''): raise RightTrianglePlanError('assets unsupported')
 c=_normalized_content(context); cond=_section(c,'condition'); ans=_section(c,'answer'); sol=_section(c,'solution')
 soup=BeautifulSoup(str(cond.get('html') if cond else ''),'html.parser'); spans=soup.find_all('span')
 if not cond or c.get('assets') or len(spans)!=1: raise RightTrianglePlanError('condition unsupported')
 f=str(spans[0].get('data-inline-latex') or ''); z=_R.fullmatch(f)
 text=soup.get_text(' ',strip=True).replace('\u00ad',''); bigger='больший' in text; smaller='меньший' in text
 if not z or bigger==smaller: raise RightTrianglePlanError('condition unsupported')
 v={k:int(z.group(k)) for k in ('a','b')}
 if z.group('m'):
  q=int(z.group('q')); imp=int(z.group('m'))*q+int(z.group('p')); rhs=Fraction(imp,q)
 else:
  imp=int(z.group('n')); q=int(z.group('d')); rhs=Fraction(imp,q)
 sq=rhs/Fraction(v['a'],v['b'])
 rn, rd = math.isqrt(sq.numerator), math.isqrt(sq.denominator)
 if rn*rn != sq.numerator or rd*rd != sq.denominator: raise RightTrianglePlanError('root unsupported')
 root=Fraction(rn,rd) if bigger else -Fraction(rn,rd); out=str(root.numerator) if root.denominator==1 else f"{'-' if root.numerator<0 else ''}{abs(root.numerator)*10//root.denominator//10},{abs(root.numerator)*10//root.denominator%10}"; r=rn
 html=f'<p>Пе­ре­ве­дем число в пра­вой части урав­не­ния в не­пра­виль­ную дробь и умно­жим обе части урав­не­ния на {v["b"]}, по­лу­ча­ем:</p><center><p><span data-inline-latex="{f}\\iff \\frac{{{v["a"]}}}{{{v["b"]}}}x^{{2}}=\\frac{{{imp}}}{{{q}}}\\iff x^{{2}}={r*r}\\iff \\left[\\begin{{aligned}}x={r}\\\\x=-{r}\\end{{aligned}}\\right."></span>.</p></center>'
 changes=[]
 if sol is None or str(sol.get('html') or '')!=html: changes.append(_section_transformation(sol,'solution','Решение',html))
 actual=BeautifulSoup(str(ans.get('html') if ans else ''),'html.parser').get_text('',strip=True)
 if actual!=out: changes.append(_section_transformation(ans,'answer','Ответ',f'<p><span data-effect="spaced">{out}</span></p>'))
 return RepairPlan(answer=out,transformations=tuple(changes))
