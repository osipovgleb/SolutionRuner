"""Exact single-quadratic solver with audited graphical or interval choices."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from fractions import Fraction
import hashlib
from html import escape
import json
from math import isqrt
from pathlib import Path
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from .inequality_systems import condition_fingerprint
from .inequality_systems_complete import RepairPlan
from .inequality_system_svg import render_quadratic_sign_chart_svg
from .linear_system_intervals import Interval, interval_latex, number, relation_latex
from .quadratic_inequality_choices import QuadraticChoice

RULE = 'quadratic-single-interval-choices'
ASSET_KEY = 'generated_quadratic_solution'
_EVIDENCE_PATH = Path(__file__).with_name('quadratic_interval_choices_evidence.json')
_EVIDENCE = json.loads(_EVIDENCE_PATH.read_text())


def normalized_math(raw: str) -> str:
    raw = raw.replace('{,}', '.').replace('−','-').replace('–','-').replace('\u200b','')
    raw = re.sub(r'\\frac\{(-?\d+)\}\{(\d+)\}', r'(\1/\2)', raw)
    for command, operator in ((r'\leqslant','<='),(r'\geqslant','>='),(r'\leq','<='),(r'\geq','>='),
                              (r'\le','<='),(r'\ge','>='),(r'\lt','<'),(r'\gt','>'),(r'\cdot','*')):
        raw = raw.replace(command,operator)
    return re.sub(r'\s+', '', raw).replace('{','').replace('}','')


def _polynomial(raw: str) -> tuple[Fraction, Fraction, Fraction]:
    """Evaluate a bounded arithmetic AST, never arbitrary source expressions."""
    if len(raw)>200 or not re.fullmatch(r'[0-9x+*/().^\-]+',raw):
        raise ValueError('unsupported polynomial expression')
    raw = re.sub(r'(?<=[\dx)])(?=[x(])', '*', raw).replace('^','**')
    def evaluate(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):
            return (Fraction(ast.get_source_segment(raw,node)),Fraction(0),Fraction(0))
        if isinstance(node,ast.Name) and node.id=='x':
            return (Fraction(0),Fraction(1),Fraction(0))
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
            value=evaluate(node.operand)
            return tuple(-v for v in value) if isinstance(node.op,ast.USub) else value
        if isinstance(node,ast.BinOp):
            left,right=evaluate(node.left),evaluate(node.right)
            if isinstance(node.op,(ast.Add,ast.Sub)):
                return tuple(a-b if isinstance(node.op,ast.Sub) else a+b for a,b in zip(left,right))
            if isinstance(node.op,ast.Div) and right[0] and not any(right[1:]):
                return tuple(v/right[0] for v in left)
            if isinstance(node.op,ast.Pow):
                if right != (2,0,0):raise ValueError('only squares are supported')
                right=left
            elif not isinstance(node.op,ast.Mult):
                raise ValueError('unsupported polynomial operator')
            product=[sum(left[i]*right[j] for i in range(3) for j in range(3) if i+j==degree) for degree in range(5)]
            if any(product[3:]):raise ValueError('degree exceeds two')
            return tuple(product[:3])
        raise ValueError('unsupported polynomial syntax')
    return evaluate(ast.parse(raw,mode='eval').body)


def _polynomial_latex(a: Fraction,b: Fraction,c: Fraction) -> str:
    parts=[]
    for coefficient,suffix in ((a,'x^{2}'),(b,'x'),(c,'')):
        if not coefficient:continue
        sign='-' if coefficient<0 else '+' if parts else ''
        magnitude='' if suffix and abs(coefficient)==1 else number(abs(coefficient))
        parts.append(sign+magnitude+suffix)
    return ''.join(parts) or '0'


@dataclass(frozen=True)
class SolvedQuadratic:
    choice: QuadraticChoice
    stages: tuple[str,...]


def solve_quadratic(latex: str) -> SolvedQuadratic:
    raw=normalized_math(latex)
    pieces=re.split(r'(<=|>=|<|>)',raw)
    if len(pieces)!=3:raise ValueError('exactly one inequality is required')
    left,relation,right=pieces
    c,b,a=tuple(u-v for u,v in zip(_polynomial(left),_polynomial(right)))
    if not a:raise ValueError('a genuine quadratic is required')
    if a<0:
        a,b,c=-a,-b,-c
        relation={'<':'>','>':'<','<=':'>=','>=':'<='}[relation]
    stages=[latex]
    moved=_polynomial_latex(a,b,c)+relation_latex(relation)+'0'
    if normalized_math(moved)!=raw:stages.append(moved)
    # Reuse the established sign-chart representation with exact rational roots.
    discriminant=b*b-4*a*c
    if discriminant<=0:raise ValueError('single-choice groups currently require two distinct real roots')
    numerator,denominator=isqrt(discriminant.numerator),isqrt(discriminant.denominator)
    if numerator*numerator!=discriminant.numerator or denominator*denominator!=discriminant.denominator:
        raise ValueError('irrational roots require separate support')
    square_root=Fraction(numerator,denominator)
    lower,upper=(-b-square_root)/(2*a),(-b+square_root)/(2*a)
    closed=relation.endswith('=')
    intervals=(Interval(lower,upper,closed,closed),) if relation.startswith('<') else (
        Interval(upper=lower,upper_closed=closed),Interval(lower=upper,lower_closed=closed))
    def factor(root):
        q,p=root.denominator,root.numerator
        variable='x' if q==1 else str(q)+'x'
        return variable if not p else '('+variable+('+' if p<0 else '-')+str(abs(p))+')'
    factored=factor(lower)+factor(upper)+relation_latex(relation)+'0'
    if '(' in left and ')' in left and right=='0':
        stages=[latex] if _polynomial(left)[2]>0 else stages
    elif normalized_math(factored)!=normalized_math(stages[-1]):stages.append(factored)
    choice=QuadraticChoice(latex,factored,intervals,(lower,upper))
    return SolvedQuadratic(choice,tuple(stages))


def parse_interval_option(raw: str) -> tuple[Interval,...]:
    raw=raw.replace('\xad','').replace('−','-').replace('–','-').replace('∞','inf').replace('∪','U')
    raw=raw.replace(r'\infty','inf').replace(r'\cup','U').replace(r'\left','').replace(r'\right','')
    raw=re.sub(r'\\frac\{(-?\d+)\}\{(\d+)\}',r'\1/\2',raw)
    raw=re.sub(r'\s+','',raw).replace('{,}', '.').replace(',','.')
    raw=re.sub(r'^\d[).]','',raw)
    if raw in ('нетрешений','решенийнет',r'\varnothing','∅'):return ()
    if raw in ('R',r'\mathbb{R}'):return (Interval(),)
    result=[]
    for part in raw.split('U'):
        match=re.fullmatch(r'([\[(])([^;]+);([^;]+)([\])])',part)
        if not match:raise ValueError('unsupported interval option')
        lb,low,high,ub=match.groups()
        lower=None if low=='-inf' else Fraction(low)
        upper=None if high in ('+inf','inf') else Fraction(high)
        lc,uc=lb=='[',ub==']'
        if lower is None and lc or upper is None and uc:raise ValueError('infinite boundary cannot be closed')
        if lower is not None and upper is not None and lower>=upper:raise ValueError('unordered interval boundaries')
        result.append(Interval(lower,upper,lc,uc))
    return tuple(result)


def extract_formula(condition_html: str) -> str:
    soup=BeautifulSoup(condition_html,'html.parser')
    for tag in soup.find_all('span',attrs={'data-inline-latex':True}):
        latex=tag['data-inline-latex']
        if re.search(r'\\(?:lt|gt|le|ge)|[<>]',latex) and 'x' in latex:return latex
    paragraph=soup.find('p')
    if paragraph is None:raise ValueError('condition formula is missing')
    paragraph=BeautifulSoup(str(paragraph),'html.parser')
    for power in paragraph.find_all('sup'):power.replace_with('^{'+power.get_text()+'}')
    text=paragraph.get_text('',strip=True).replace('\xad','').replace('\u200b','').replace('−','-')
    match=re.search(r'(x\^\{2\}\s*[+-]\s*\d+\s*[<>]=?\s*0)',text)
    if not match:raise ValueError('condition formula is missing')
    return re.sub(r'\s+','',match[1])


def _verified(context: dict[str,Any]) -> tuple[SolvedQuadratic,str]:
    record=_EVIDENCE.get(str(context.get('problem_id')))
    if record is None:raise ValueError('single-quadratic choices have not been audited')
    if record.get('blocked_reason'):raise ValueError(record['blocked_reason'])
    condition=_section(_normalized_content(context),'condition')
    if condition is None or condition_fingerprint(condition['html'])!=record['condition_sha256']:
        raise ValueError('condition or option order changed since review')
    formula=extract_formula(condition['html'])
    if normalized_math(formula)!=normalized_math(record['formula']):raise ValueError('condition formula changed')
    solved=solve_quadratic(formula)
    target=[list(i.key()) for i in solved.choice.intervals]
    matches=[str(index) for index,option in enumerate(record['choices'],1) if option==target]
    if len(matches)!=1:raise ValueError('solved inequality must match exactly one audited option')
    return solved,matches[0]


def diagram_specs(context: dict[str,Any]) -> tuple[dict[str,str],...]:
    solved,_=_verified(context)
    svg=render_quadratic_sign_chart_svg(solved.choice.roots,solved.choice.intervals)
    return ({'asset_key':ASSET_KEY,'svg_text':svg.decode(),'sha256':hashlib.sha256(svg).hexdigest()},)


def build_context_repair_plan(context: dict[str,Any], *, generated_solution_assets: tuple[dict[str,str],...]=()) -> RepairPlan:
    solved,expected=_verified(context)
    content=_normalized_content(context)
    condition=_section(content,'condition');solution=_section(content,'solution');answer=_section(content,'answer')
    changes=[];keys=[];diagram=''
    if generated_solution_assets:
        if len(generated_solution_assets)!=1 or generated_solution_assets[0]['asset_key']!=ASSET_KEY:
            raise ValueError('one quadratic solution diagram is required')
        asset=generated_solution_assets[0];keys=[ASSET_KEY]
        markup=(f'<img alt="Метод интервалов" data-asset-key="{ASSET_KEY}" data-asset-id="{asset["source_asset_id"]}" src="{asset["url"]}"/>')
        diagram='<center>'+markup+'</center>'
        existing=next((a for a in content.get('assets',[]) if a.get('asset_key')==ASSET_KEY),None)
        if existing is None or existing.get('asset_id')!=asset['source_asset_id']:
            changes.append({'transformation_target_id':'asset:'+ASSET_KEY,'operation':'add',
                            'value':{'asset_key':ASSET_KEY,'asset_id':asset['source_asset_id'],'url':asset['url'],
                                     'html':markup,'kind':'ordinary_image','alt':'Метод интервалов',
                                     'parent_target_id':'section:solution:1','position':0}})
    condition_keys=set(condition.get('asset_keys') or [])
    for key in solution.get('asset_keys',[]) if solution else []:
        if key!=ASSET_KEY and key not in condition_keys:
            changes.append({'transformation_target_id':'asset:'+key,'operation':'remove'})
    chain=r'\iff '.join(solved.stages)
    result=r'\cup'.join(interval_latex(i) for i in solved.choice.intervals)
    html=('<p>Решим неравенство методом интервалов:</p><center><p><span data-inline-latex="'
          +escape(chain,quote=True)+'"></span>.</p></center>'+diagram
          +'<center><p><span data-inline-latex="'+escape(r'x\in '+result,quote=True)+'"></span>.</p></center><br/>')
    if (solution is None or condition_fingerprint(str(solution.get('html') or ''))!=condition_fingerprint(html)
            or list(solution.get('asset_keys') or [])!=keys):
        changes.append(_section_transformation(solution,'solution','Решение',html,asset_keys=tuple(keys)))
    current=BeautifulSoup(answer['html'],'html.parser').get_text('',strip=True) if answer else ''
    if current!=expected:
        changes.append(_section_transformation(answer,'answer','Ответ',f'<p><span data-effect="spaced">{expected}</span></p>'))
    return RepairPlan(expected,tuple(changes))
