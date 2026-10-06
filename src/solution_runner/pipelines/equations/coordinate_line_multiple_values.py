"""Concrete, scale-respecting substitutions for a short coordinate-line task."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RightTrianglePlanError

_POINT = re.compile(r'<path\b(?=[^>]*\bfill=["\']#143B8F["\'])(?=[^>]*\bd=["\']M([-\d.]+),([-\d.]+))[^>]*>')
_ZERO = re.compile(r'<line\b[^>]*\bx1=["\']([-\d.]+)["\'][^>]*\bx2=["\']\1["\'][^>]*>')

@dataclass(frozen=True)
class RepairPlan:
    answer: str
    transformations: tuple[dict[str, Any], ...]

def _values(svg: bytes, names: list[str]) -> dict[str, int]:
    text=svg.decode('utf-8')
    zeroes=[float(x) for x in _ZERO.findall(text)]
    points=sorted({float(x) for x,_ in _POINT.findall(text)})
    if len(zeroes)!=1 or len(points)!=len(names):
        raise RightTrianglePlanError('coordinate line markers are not reviewed')
    distances=[abs(point-zeroes[0]) for point in points]
    unit=min(distances)
    # In the x/y template the labels are placed from right to left; the a/b/c
    # templates follow the line from left to right.
    if names == ["x", "y"]:
        points.reverse()
    result={name:round((point-zeroes[0])/unit) for name,point in zip(names,points)}
    if not unit or any(value==0 for value in result.values()):
        raise RightTrianglePlanError('coordinate line scale is ambiguous')
    return result

def _options(condition: dict[str, Any]) -> list[tuple[str,str]]:
    soup=BeautifulSoup(str(condition.get('html') or ''),'html.parser')
    items=soup.find_all('li') or soup.find_all('nobr')
    if len(items)!=4:
        items=[tag for tag in soup.find_all('p') if re.match(r'\s*\d+\)',tag.get_text())]
    result=[]
    for item in items:
        latex=item.find('span',attrs={'data-inline-latex':True})
        raw=str(latex.get('data-inline-latex') if latex else item.get_text('',strip=True))
        raw=re.sub(r'^\d+\)','',raw).replace('−','-').replace(r'\gt','>').replace(r'\lt','<').replace('{','').replace('}','').replace(' ','')
        match=re.fullmatch(r'([abcxy0-9+\-^]+)([<>])0',raw)
        if not match: raise RightTrianglePlanError('option is not a reviewed sign expression')
        result.append((match.group(1),match.group(2)))
    if len(result)!=4: raise RightTrianglePlanError('condition must contain four options')
    return result

def _evaluate(expression: str, values: dict[str,int]) -> int:
    python=re.sub(r'([abcxy])(?=[abcxy])',r'\1*',expression).replace('^','**')
    python=re.sub(r'(?<=\d)(?=[abcxy])','*',python)
    python=re.sub(r'[abcxy]',lambda match:f'({values[match.group()]})',python)
    try: return int(eval(python,{'__builtins__':{}},values))
    except Exception as exc: raise RightTrianglePlanError('option expression is invalid') from exc

def _vertical(condition: dict[str, Any]) -> str | None:
    soup=BeautifulSoup(str(condition.get('html') or ''),'html.parser'); rows=soup.find_all('nobr')
    if len(rows)!=4:return None
    ol=soup.new_tag('ol',attrs={'data-layout':'source-options'})
    for i,row in enumerate(rows,1):
        li=soup.new_tag('li'); li.append(BeautifulSoup(re.sub(rf'^\s*{i}\)\s*','',row.decode_contents()),'html.parser')); ol.append(li)
    rows[0].replace_with(ol)
    for row in rows[1:]:row.extract()
    return str(soup)

def build_context_repair_plan(context: dict[str,Any], *, condition_asset_bytes: bytes|None) -> RepairPlan:
    content=_normalized_content(context); condition=_section(content,'condition'); answer_section=_section(content,'answer'); solution=_section(content,'solution')
    if condition is None or condition_asset_bytes is None: raise RightTrianglePlanError('condition SVG is required')
    intro=BeautifulSoup(str(condition.get('html') or ''),'html.parser').find('p')
    names=[] if intro is None else list(dict.fromkeys(re.findall(r'\b([abcxy])\b',intro.get_text(' ',strip=True))))
    if len(names) not in (2,3): raise RightTrianglePlanError('coordinate variables are unavailable')
    values=_values(condition_asset_bytes,names); options=_options(condition)
    results=[_evaluate(expr,values) for expr,_ in options]
    prompt=BeautifulSoup(str(condition.get('html') or ''),'html.parser').get_text(' ',strip=True).replace('\u00ad','').lower()
    wrong='неверно' in prompt
    selected=[i+1 for i,((_,sign),value) in enumerate(zip(options,results)) if (value<0 if sign=='>' else value>0) == wrong]
    if len(selected)!=1: raise RightTrianglePlanError('options do not select one answer')
    rows=[]
    for (expr,sign),value in zip(options,results):
        displayed=expr
        for name,number in values.items(): displayed=displayed.replace(name,f'({number})')
        rows.append(f'<li><span data-inline-latex="{displayed}={value}{sign}0"></span> — {"верно" if (value>0 if sign==">" else value<0) else "неверно"}.</li>')
    assigned=',\\ '.join(f'{name}={number}' for name,number in values.items())
    verdict='неверно' if wrong else 'верно'
    html=f'<p>По рисунку возьмём <span data-inline-latex="{assigned}"></span>. Проверим утверждения.</p><ol data-layout="source-options">{"".join(rows)}</ol><p>Таким образом, утверждение {selected[0]} {verdict}.</p>'
    changes=[]
    if vertical:=_vertical(condition): changes.append(_section_transformation(condition,'condition','Условие',vertical))
    changes.append(_section_transformation(solution,'solution','Решение',html))
    answer=BeautifulSoup(str(answer_section.get('html') or '') if answer_section else '', 'html.parser').get_text('',strip=True)
    if answer!=str(selected[0]): changes.append(_section_transformation(answer_section,'answer','Ответ',f'<p><span data-effect="spaced">{selected[0]}</span></p>'))
    return RepairPlan(str(selected[0]),tuple(changes))
