"""Fail-closed reciprocal linear-equation solver for group 77383."""
from __future__ import annotations
from fractions import Fraction
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content,_section,_section_transformation
from ..triangles.right.planner import RepairPlan,RightTrianglePlanError
from .linear_fraction import solve_reciprocal_linear_equation
RULE='elementary-equations-77383-reciprocal-linear'
_F=re.compile(r'\\frac\{(?P<n>-?\d+)\}\{(?P<a>-?\d*)x(?P<s>[+-])(?P<b>\d+)\}=(?:\\frac\{(?P<m>-?\d+)\}\{(?P<c>-?\d+)\}|(?P<r>-?\d+))')
def _n(v:Fraction)->str:
 if v.denominator==1:return str(v.numerator)
 d=v.denominator
 while d%2==0:d//=2
 while d%5==0:d//=5
 if d!=1:raise RightTrianglePlanError('root has infinite decimal')
 sign='-' if v<0 else ''; q=0; den=v.denominator
 while den>1:den=den//2 if den%2==0 else den//5;q+=1
 z=str(abs(v.numerator)*10**q//v.denominator).zfill(q+1);return sign+z[:-q]+','+z[-q:]
def build_repair_plan(context:dict[str,Any],*,parent_condition_asset_id:str|None,parent_solution_html:str='',current_asset_content_type:str|None=None)->RepairPlan:
 del parent_solution_html,current_asset_content_type
 if parent_condition_asset_id not in (None,''):raise RightTrianglePlanError('group 77383 must not have assets')
 c=_normalized_content(context);q=_section(c,'condition');ans=_section(c,'answer');sol=_section(c,'solution')
 if q is None or c.get('assets') or tuple(q.get('asset_keys') or ()):raise RightTrianglePlanError('condition incomplete')
 soup=BeautifulSoup(str(q.get('html') or ''),'html.parser');sp=soup.find_all('span')
 if len(sp)!=1 or sp[0].get_text(strip=True):raise RightTrianglePlanError('condition ambiguous')
 f=str(sp[0].get('data-inline-latex') or '');m=_F.fullmatch(f)
 if not m:raise RightTrianglePlanError('condition does not match group 77383')
 n=int(m['n']);a=int(m['a'] or '1');b=int(m['b']) if m['s']=='+' else -int(m['b'])
 if m['r'] is None:
  right=int(m['c']);numerator_right=int(m['m']);left_product=n*right
 else:
  right=1;numerator_right=int(m['r']);left_product=n
 if not n or not a or not right or not numerator_right:raise RightTrianglePlanError('zero denominator coefficient')
 try:root=solve_reciprocal_linear_equation(Fraction(n),Fraction(a),Fraction(b),Fraction(numerator_right,right))
 except ValueError as exc:raise RightTrianglePlanError(str(exc)) from exc
 value=_n(root);left_linear=f'{a if a!=1 else ""}x{m["s"]}{abs(b)}';coefficient=numerator_right*a;constant=numerator_right*b;rhs=left_product-constant
 h='<p>По­сле­до­ва­тель­но по­лу­ча­ем:</p>'+f'<center><p><span data-inline-latex="{f}\\iff {left_product}={numerator_right}\\cdot({left_linear})\\iff {left_product}={coefficient}x{("+" if constant>=0 else "-")}{abs(constant)}\\iff {coefficient}x={rhs}\\iff x={value.replace(",","{,}")}"></span>.</p></center>'
 ch=[]
 if sol is None or sol.get('html')!=h:ch.append(_section_transformation(sol,'solution','Решение',h))
 cur=BeautifulSoup(str(ans.get('html') or '') if ans else '','html.parser').get_text('',strip=True).replace(' ','')
 if cur!=value:ch.append(_section_transformation(ans,'answer','Ответ',f'<p><span data-effect="spaced">{value}</span></p>'))
 return RepairPlan(answer=value,transformations=tuple(ch))
