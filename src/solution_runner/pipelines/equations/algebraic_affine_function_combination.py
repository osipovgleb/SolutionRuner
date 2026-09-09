"""Evaluate C(p(mx)-m p(x+h)) for p(x)=x+d."""
from __future__ import annotations
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content,_section,_section_transformation
from ..triangles.right.planner import RepairPlan,RightTrianglePlanError
T=re.compile(r"^(?P<c>\d+)\(p\((?P<m>\d*)x\)-(?P=m)p\(x(?P<s>[+-])(?P<h>\d+)\)\)$")
F=re.compile(r"^p\(x\)=x(?P<d>[+-]\d+)$")
def plan(context:dict[str,Any])->RepairPlan:
 c=_normalized_content(context); q=_section(c,'condition'); s=BeautifulSoup(str(q.get('html') or ''),'html.parser'); z=[str(v.get('data-inline-latex') or '').replace(' ','') for v in s.find_all('span',attrs={'data-inline-latex':True})]
 if len(z)!=2: raise RightTrianglePlanError('condition must contain expression and function')
 t,f=T.fullmatch(z[0]),F.fullmatch(z[1])
 if not t or not f: raise RightTrianglePlanError('condition does not match affine function combination')
 C,m,h,d=int(t['c']),int(t['m'] or '1'),int(t['h']),int(f['d']); shift=h if t['s']=='+' else -h; inside=d-m*(shift+d); ans=C*inside
 main=f"p({m}x)={m}x{d:+d},\\quad p(x{t['s']}{h})=x{shift+d:+d}".replace('+-','-'); substituted=f"{z[0]}={C}(({m}x{d:+d})-{m}(x{shift+d:+d}))".replace('+-','-'); calc=f"{substituted}={C}({m}x{d:+d}-{m}x{(-m*(shift+d)):+d})={C}({inside})={ans}".replace('+-','-')
 a,b=m,1+shift; va,vb=a+d,b+d
 html=f'<p>Найдём значения функции:</p><center><p><span data-inline-latex="{main}"></span>.</p></center><p>Следовательно,</p><center><p><span data-inline-latex="{substituted}"></span>.</p></center><p>Раскроем внутренние скобки:</p><center><p><span data-inline-latex="{calc}"></span>.</p></center><p><b>Приведём другое решение</b></p><p>Так как это задание первой части, переменная <span data-inline-latex="x"></span> в ответе быть не может, значит, она должна сократиться.</p><p>Подставим <span data-inline-latex="x=1"></span>:</p><center><p><span data-inline-latex="{C}(p({a})-{m}p({b})"></span>.</p></center><p>Найдём значения функции:</p><center><p><span data-inline-latex="p({a})={va}"></span>.</p></center><center><p><span data-inline-latex="p({b})={vb}"></span>.</p></center><p>Подставим найденные значения:</p><center><p><span data-inline-latex="{C}({va}-{m}\\cdot({vb}))={ans}"></span>.</p></center>'
 anssec=_section(c,'answer'); sol=_section(c,'solution'); ch=[]
 if sol is None or str(sol.get('html') or '')!=html: ch.append(_section_transformation(sol,'solution','Решение',html))
 now=BeautifulSoup(str(anssec.get('html') or '') if anssec else '','html.parser').get_text('',strip=True).replace(' ','')
 if now!=str(ans): ch.append(_section_transformation(anssec,'answer','Ответ',f'<p><span data-effect="spaced">{ans}</span></p>'))
 return RepairPlan(answer=str(ans),transformations=tuple(ch))
build_context_repair_plan=plan
