from __future__ import annotations
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content,_section,_section_transformation
from ..triangles.right.planner import RepairPlan,RightTrianglePlanError
RULE='elementary-equations-282850-odd-power-root'
R=re.compile(r'(?:(?:\(x(?P<s>[+-]\d+)\))|x)\^\{(?P<n>3|5|9)\}=(?P<r>-?\d+)')


def _integer_root(value: int, degree: int) -> int:
    """Return the exact odd-degree integer root, rejecting non-perfect powers."""
    magnitude = abs(value)
    low, high = 0, max(1, magnitude)
    while low <= high:
        middle = (low + high) // 2
        powered = middle**degree
        if powered == magnitude:
            return -middle if value < 0 else middle
        if powered < magnitude:
            low = middle + 1
        else:
            high = middle - 1
    raise RightTrianglePlanError('root unsupported')


def build_repair_plan(context:dict[str,Any],*,parent_condition_asset_id:str|None,parent_solution_html:str='',current_asset_content_type:str|None=None)->RepairPlan:
 del parent_solution_html,current_asset_content_type
 c=_normalized_content(context); q=_section(c,'condition'); a=_section(c,'answer'); z=BeautifulSoup(str(q.get('html') if q else ''),'html.parser').find('span'); m=R.fullmatch(str(z.get('data-inline-latex') if z else ''))
 if not q or c.get('assets') or not m: raise RightTrianglePlanError('condition unsupported')
 s,n,r=int(m['s'] or 0),int(m['n']),int(m['r']); k=_integer_root(r,n)
 x=k-s; f=str(z['data-inline-latex']); left=f'x{s:+d}'.replace('+-','-') if s else 'x'; h=f'<p>Из­вле­кая ко­рень степени {n} из обеих ча­стей урав­не­ния, по­лу­ча­ем <span data-inline-latex="{left}={k}"></span>, от­ку­да <span data-inline-latex="x={x}"></span>.</p>'
 ch=[_section_transformation(_section(c,'solution'),'solution','Решение',h)] if not _section(c,'solution') or _section(c,'solution').get('html')!=h else []
 if BeautifulSoup(str(a.get('html') if a else ''),'html.parser').get_text('',strip=True)!=str(x): ch.append(_section_transformation(a,'answer','Ответ',f'<p><span data-effect="spaced">{x}</span></p>'))
 return RepairPlan(answer=str(x),transformations=tuple(ch))
