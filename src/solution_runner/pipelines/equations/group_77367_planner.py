"""Fail-closed quadratic rational-equation solver for group 77367."""
from __future__ import annotations
from fractions import Fraction
import math, re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content,_section,_section_transformation
from ..triangles.right.planner import RepairPlan,RightTrianglePlanError
RULE="elementary-equations-77367-rational-quadratic-selector"
_F=re.compile(r"\\frac\{(?P<p>\d*)x\}\{(?P<a>\d*)x\^\{2\}(?P<s>[+-])(?P<b>\d+)\}=(?P<q>[1-9]\d*)")
_K=re.compile(r"в ответе запишите (?P<k>больший|меньший) из корней\.?$")
def _n(v:Fraction)->str:
 if v.denominator==1:return str(v.numerator)
 d=v.denominator
 while d%2==0:d//=2
 while d%5==0:d//=5
 if d!=1:raise RightTrianglePlanError("root has infinite decimal")
 s='-' if v<0 else ''; n=abs(v.numerator); den=v.denominator; q=0
 while den>1:den=den//2 if den%2==0 else den//5;q+=1
 z=str(n*10**q//v.denominator).zfill(q+1);return s+z[:-q]+','+z[-q:]
def _latex(v:Fraction)->str:
 return str(v.numerator) if v.denominator==1 else f'\\frac{{{v.numerator}}}{{{v.denominator}}}'
def build_repair_plan(context:dict[str,Any],*,parent_condition_asset_id:str|None,parent_solution_html:str='',current_asset_content_type:str|None=None)->RepairPlan:
 del parent_solution_html,current_asset_content_type
 if parent_condition_asset_id not in (None,''):raise RightTrianglePlanError('group 77367 must not have assets')
 c=_normalized_content(context);q=_section(c,'condition');ans=_section(c,'answer');sol=_section(c,'solution')
 if q is None or c.get('assets') or tuple(q.get('asset_keys') or ()):raise RightTrianglePlanError('condition incomplete')
 soup=BeautifulSoup(str(q.get('html') or ''),'html.parser');sp=soup.find_all('span')
 if len(sp)!=1 or sp[0].get_text(strip=True):raise RightTrianglePlanError('condition ambiguous')
 f=str(sp[0].get('data-inline-latex') or '');m=_F.fullmatch(f); text=' '.join(soup.get_text(' ',strip=True).replace('\u00ad','').split());k=_K.search(text)
 if not m or not k:raise RightTrianglePlanError('condition does not match group 77367')
 p=int(m['p'] or '1');a=int(m['a'] or '1');b=int(m['b']);q_value=int(m['q']);sign=m['s'];constant=b if sign=='+' else -b;quadratic_a=q_value*a;quadratic_c=q_value*constant;d=p*p-4*quadratic_a*quadratic_c
 if d<0:raise RightTrianglePlanError('discriminant is negative')
 r=math.isqrt(d)
 if r*r!=d:raise RightTrianglePlanError('discriminant is not square')
 roots=sorted((Fraction(p-r,2*quadratic_a),Fraction(p+r,2*quadratic_a)))
 valid_roots=tuple(v for v in roots if a*v*v+constant!=0)
 if not valid_roots:raise RightTrianglePlanError('no roots satisfy the domain')
 chosen=valid_roots[-1] if k['k']=='больший' else valid_roots[0]
 rows='\\\\'.join(f'x={_latex(v).replace(",","{,}")}' for v in (roots[1],roots[0])); atext=_n(chosen)
 lhs=(str(a) if a!=1 else '')+'x^{2}';px=(str(p) if p!=1 else '')+'x'
 domain_rhs=(-b if sign=='+' else b)
 d_sub=f'(-{p})^{{2}}-4\\cdot{quadratic_a}\\cdot' + (str(quadratic_c) if quadratic_c>=0 else f'({quadratic_c})')
 radicand=f'{p*p}{"-" if 4*quadratic_a*quadratic_c>=0 else "+"}{abs(4*quadratic_a*quadratic_c)}'
 root_rows='\\\\'.join(f'x=\\frac{{{p}{"+" if sign_value>0 else "-"}\\sqrt{{{radicand}}}}}{{{2*quadratic_a}}}' for sign_value in (1,-1))
 selector='боль­ший' if k['k']=='больший' else 'мень­ший'
 h='<p>Об­ласть опре­де­ле­ния урав­не­ния за­да­ет­ся со­от­но­ше­ни­ем <span data-inline-latex="'+f'{lhs}\\ne {domain_rhs}'+'"></span>. На об­ла­сти опре­де­ле­ния имеем:</p>'+f'<center><p><span data-inline-latex="{f}\\iff {px}={q_value}\\cdot({lhs}{sign}{b})\\iff {quadratic_a}x^{{2}}-{px}{sign}{abs(quadratic_c)}=0"></span>.</p></center><p>Вос­поль­зу­ем­ся фор­му­лой дис­кри­ми­нан­та:</p><center><p><span data-inline-latex="D=b^2-4ac={d_sub}={d}"></span>.</p></center><p>Вос­поль­зу­ем­ся фор­му­лой для кор­ней квад­рат­но­го урав­не­ния:</p>'+f'<center><p><span data-inline-latex="\\left[\\begin{{aligned}}{root_rows}\\end{{aligned}}\\right.\\iff \\left[\\begin{{aligned}}{rows}\\end{{aligned}}\\right."></span>.</p></center><p>Оба най­ден­ных ре­ше­ния удо­вле­тво­ря­ют усло­вию <span data-inline-latex="{lhs}\\ne {domain_rhs}"></span>, {selector} из них равен {atext}.</p>'
 ch=[]
 if sol is None or sol.get('html')!=h:ch.append(_section_transformation(sol,'solution','Решение',h))
 cur=BeautifulSoup(str(ans.get('html') or '') if ans else '','html.parser').get_text('',strip=True).replace(' ','')
 if cur!=atext:ch.append(_section_transformation(ans,'answer','Ответ',f'<p><span data-effect="spaced">{atext}</span></p>'))
 return RepairPlan(answer=atext,transformations=tuple(ch))
