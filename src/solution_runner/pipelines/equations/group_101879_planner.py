"""Equal-fractions planner for group 101879."""
from __future__ import annotations
from fractions import Fraction
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content,_section,_section_transformation
from ..triangles.right.planner import RepairPlan,RightTrianglePlanError
RULE='elementary-equations-101879-equal-numerators'
_D=r'\d+(?:\{,\}\d+)?'
_F=re.compile(rf'\\frac\{{x(?P<ns>[+-])(?P<n>{_D})\}}\{{(?P<a>-?(?:{_D})?)x(?P<as>[+-])(?P<b>{_D})\}}=\\frac\{{x(?P<ns2>[+-])(?P<n2>{_D})\}}\{{(?P<c>-?(?:{_D})?)x(?:(?P<cs>[+-])(?P<d>{_D}))?\}}')
_K=re.compile(r'в ответ(?:е)? запишите (?P<k>больший|меньший)(?: из)? (?:корень|корней)\.?$')
def build_repair_plan(context:dict[str,Any],*,parent_condition_asset_id:str|None,parent_solution_html:str='',current_asset_content_type:str|None=None)->RepairPlan:
 del parent_solution_html,current_asset_content_type
 if parent_condition_asset_id not in (None,''):raise RightTrianglePlanError('group 101879 must not have assets')
 c=_normalized_content(context);q=_section(c,'condition');ans=_section(c,'answer');sol=_section(c,'solution')
 if q is None or c.get('assets') or tuple(q.get('asset_keys') or ()):raise RightTrianglePlanError('condition incomplete')
 soup=BeautifulSoup(str(q.get('html') or ''),'html.parser');sp=soup.find_all('span')
 if len(sp)!=1 or sp[0].get_text(strip=True):raise RightTrianglePlanError('condition ambiguous')
 f=str(sp[0].get('data-inline-latex') or '');m=_F.fullmatch(f);text=' '.join(soup.get_text(' ',strip=True).replace('\u00ad','').split());k=_K.search(text)
 if not m or not k or m['ns']!=m['ns2'] or m['n']!=m['n2']:raise RightTrianglePlanError('condition does not match group 101879')
 val=lambda s: Fraction(str(s).replace('{,}','.'))
 n=val(m['n']) if m['ns']=='+' else -val(m['n']);a=val(m['a'] or '1');b=val(m['b']) if m['as']=='+' else -val(m['b']);cc=val(m['c'] or '1');d=Fraction(0) if m['cs'] is None else (val(m['d']) if m['cs']=='+' else -val(m['d']))
 if a==cc:raise RightTrianglePlanError('equal denominators')
 roots=sorted((Fraction(-n),Fraction(d-b,a-cc)))
 roots=tuple(x for x in roots if a*x+b and cc*x+d)
 if not roots:raise RightTrianglePlanError('no roots satisfy domain')
 chosen=roots[-1] if k['k']=='больший' else roots[0]
 def fraction_num(x):
  """Render a reduced fraction, with its sign outside the fraction bar."""
  if x.denominator==1:return str(x.numerator)
  sign='-' if x<0 else ''
  return sign+f'\\frac{{{abs(x.numerator)}}}{{{x.denominator}}}'
 def num(x):
  """Render exact numbers, preferring a terminating decimal where requested."""
  if x.denominator==1:return str(x.numerator)
  denominator=x.denominator
  while denominator%2==0:denominator//=2
  while denominator%5==0:denominator//=5
  if denominator==1:
   sign='-' if x<0 else ''
   value=abs(x)
   integer,rest=divmod(value.numerator,value.denominator)
   digits=[]
   while rest:
    rest*=10;digit,rest=divmod(rest,value.denominator);digits.append(str(digit))
   return sign+str(integer)+'{,}'+''.join(digits)
  return fraction_num(x)
 def lin(coef,const):
  lead='' if coef==1 else '-' if coef==-1 else num(coef)
  base=lead+'x'
  if not const:return base
  return base+('+' if const>0 else '-')+num(abs(const))
 values='\\\\'.join('x='+num(x) for x in roots)
 left_den=lin(a,b);right_den=lin(cc,d)
 primary='<p>Дроби с оди­на­ко­вы­ми чис­ли­те­ля­ми равны в двух слу­ча­ях:</p><ol type="a"><li>зна­ме­на­те­ли этих дро­бей равны и при этом от­лич­ны от нуля;</li><li>чис­ли­те­ли дро­бей равны нулю, при этом все зна­ме­на­те­ли от­лич­ны от нуля.</li></ol><p>По­лу­ча­ем:</p>'+f'<center><p><span data-inline-latex="{f}\\iff \\begin{{cases}}{left_den}\\ne0\\\\{right_den}\\ne0\\\\\\left[\\begin{{aligned}}x{m["ns"]}{abs(n)}=0\\\\{left_den}={right_den}\\end{{aligned}}\\right.\\end{{cases}}\\iff \\left[\\begin{{aligned}}{values}\\end{{aligned}}\\right."></span>.</p></center>'+f'<p>{"Боль­ший" if k["k"]=="больший" else "Мень­ший"} из най­ден­ных кор­ней равен {num(chosen)}.</p>'
 def poly(A,B,C):
  def term(v,suffix,first=False):
   if not v:return ''
   sign='-' if v<0 else ('' if first else '+');mag=abs(v);coef='' if suffix and mag==1 else num(mag)
   return sign+coef+suffix
  return term(A,'x^{2}',True)+term(B,'x')+term(C,'')
 def neq(v): return num(v)
 ntext=lin(Fraction(1),n);left=poly(cc,cc*n+d,d*n);right=poly(a,a*n+b,b*n);quadratic=poly(cc-a,cc*n+d-a*n-b,d*n-b*n)
 first=f'\\begin{{cases}}{left_den}\\ne0\\\\{right_den}\\ne0\\\\({ntext})({right_den})=({ntext})({left_den})\\end{{cases}}'
 fraction_exclusions=f'x\\ne{fraction_num(Fraction(-b,a))}\\\\x\\ne{fraction_num(Fraction(-d,cc))}'
 decimal_exclusions=f'x\\ne{neq(Fraction(-b,a))}\\\\x\\ne{neq(Fraction(-d,cc))}'
 second=f'\\begin{{cases}}{fraction_exclusions}\\\\{left}={right}\\end{{cases}}'
 third=f'\\begin{{cases}}{decimal_exclusions}\\\\{quadratic}=0\\end{{cases}}'
 fourth=f'\\begin{{cases}}{decimal_exclusions}\\\\\\left[\\begin{{aligned}}{values}\\end{{aligned}}\\right.\\end{{cases}}'
 alternative='<p><b>Приведём другое решение</b></p><p>Используем свойство пропорции, раскроем скобки, получим квадратное уравнение:</p>'+f'<center><p><span data-inline-latex="{f}\\iff {first}\\iff {second}\\iff {third}\\iff {fourth}"></span>.</p></center>'+f'<p>{"Боль­ший" if k["k"]=="больший" else "Мень­ший"} из най­денных кор­ней равен {num(chosen)}.</p>'
 h=primary+alternative
 out=num(chosen);ch=[]
 if sol is None or sol.get('html')!=h:ch.append(_section_transformation(sol,'solution','Решение',h))
 cur=BeautifulSoup(str(ans.get('html') or '') if ans else '','html.parser').get_text('',strip=True).replace(' ','')
 if cur!=out:ch.append(_section_transformation(ans,'answer','Ответ',f'<p><span data-effect="spaced">{out}</span></p>'))
 return RepairPlan(answer=out,transformations=tuple(ch))
