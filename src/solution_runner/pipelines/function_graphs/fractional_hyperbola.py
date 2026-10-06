"""Linear-over-linear hyperbolas: source geometry, two methods and formula repair."""
from __future__ import annotations
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import re
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from ..core.errors import ContentPlanError
from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from .diagrams import svg_frame, _n
from .hyperbola import RepairPlan, _snap, latex, formula, row, answer_text

ASSET_DIR=Path(__file__).parent/'assets/fractional-hyperbolas'
NS='{http://www.w3.org/2000/svg}'


def graph_evidence(data: bytes) -> dict:
    root=ET.fromstring(data)
    ox,oy,sx,sy,view=svg_frame(data)
    lines=list(root.iter(NS+'line'))
    hs={round(float(n.get('y1')),3) for n in lines if n.get('stroke-dasharray') and abs(float(n.get('y1'))-float(n.get('y2')))<.01}
    vs={round(float(n.get('x1')),3) for n in lines if n.get('stroke-dasharray') and abs(float(n.get('x1'))-float(n.get('x2')))<.01}
    if len(hs)!=1 or len(vs)!=1:
        raise ContentPlanError('need unique horizontal and vertical asymptotes')
    k=_snap((oy-next(iter(hs)))/sy);b=_snap((ox-next(iter(vs)))/sx)
    markers=[n for n in root.iter(NS+'circle') if n.get('fill','').upper()=='#143B8F']
    audit=registry().get('audited_unmarked_graphs',{}).get(hashlib.sha256(data).hexdigest()) if not markers else None
    if not markers and not audit:raise ContentPlanError('need a marked graph point or audited source grid intersections')
    points=[(_snap((float(n.get('cx'))-ox)/sx),_snap((oy-float(n.get('cy')))/sy)) for n in markers] if markers else [tuple(map(Fraction,p)) for p in audit['points']]
    x,y=points[0]
    if x+b==0:raise ContentPlanError('marked point is on vertical asymptote')
    c=(x+b)*(y-k)
    if not c or any((px+b)*(py-k)!=c for px,py in points):
        raise ContentPlanError('graph points disagree with shifted hyperbola')
    a=c+k*b
    def inside(point):
        px,py=ox+float(point[0])*sx,oy-float(point[1])*sy
        return view[0]+3<px<view[0]+view[2]-3 and view[1]+3<py<view[1]+view[3]-3
    second=next((p for p in points[1:] if p[0]!=x),(-2*b-x,2*k-y))
    if not inside(second):
        import math
        candidates=[]
        for nx in range(math.floor((view[0]-ox)/sx),math.ceil((view[0]+view[2]-ox)/sx)+1):
            if nx==x or nx+b==0:continue
            ny=k+c/(nx+b)
            if ny.denominator==1 and inside((nx,ny)):candidates.append((Fraction(nx),ny))
        if not candidates:raise ContentPlanError('no second visible lattice point')
        second=min(candidates,key=lambda p:(abs(p[0]),abs(p[1])))
    offset=next((p for p in [(c-b,k+1),(-c-b,k-1)] if inside(p)),(x,y))
    import math
    candidates=[]
    for nx in range(math.floor((view[0]-ox)/sx),math.ceil((view[0]+view[2]-ox)/sx)+1):
        if nx in (x,second[0]) or nx+b==0:continue
        ny=k+c/(nx+b)
        if ny.denominator==1 and inside((nx,ny)):candidates.append((Fraction(nx),ny))
    if not candidates:
        for nx in range(math.floor((view[0]-ox)/sx),math.ceil((view[0]+view[2]-ox)/sx)+1):
            if nx in (x,second[0]) or nx+b==0:continue
            ny=k+c/(nx+b)
            if ny.denominator in (2,4) and inside((nx,ny)):candidates.append((Fraction(nx),ny))
    if not candidates:raise ContentPlanError('no third visible grid point')
    third=points[2] if audit else offset if offset in candidates else min(candidates,key=lambda p:(abs(p[0]),abs(p[1])))
    return {'k':k,'a':a,'b':b,'c':c,'point':(x,y),'second':second,'third':third,'offset':offset}


def annotate(data: bytes, method: str) -> bytes:
    if method not in ('points','offset'):raise ValueError(method)
    facts=graph_evidence(data);ox,oy,sx,sy,_=svg_frame(data)
    root=ET.fromstring(data);marker=next((n for n in root.iter(NS+'circle') if n.get('fill','').upper()=='#143B8F'),None)
    red='#D12626';nodes=['<g data-role="fractional-hyperbola-overlay">']
    if method=='points':
        points=[('A',float(marker.get('cx')) if marker is not None else ox+float(facts['point'][0])*sx,float(marker.get('cy')) if marker is not None else oy-float(facts['point'][1])*sy),('B',ox+float(facts['second'][0])*sx,oy-float(facts['second'][1])*sy),('C',ox+float(facts['third'][0])*sx,oy-float(facts['third'][1])*sy)]
    else:
        ux,uy=facts['offset'];px,py=ox+float(ux)*sx,oy-float(uy)*sy
        nodes.append(f'<line x1="{_n(ox-float(facts["b"])*sx)}" y1="{_n(py)}" x2="{_n(px)}" y2="{_n(py)}" stroke="{red}" stroke-width="1.8"/>')
        points=[('',px,py)]
    for label,px,py in points:
        nodes.append(f'<circle cx="{_n(px)}" cy="{_n(py)}" r="{_n((float(marker.get("r")) if marker is not None else 2.5)+.5)}" fill="{red}"/>')
        if label:nodes.append(f'<text x="{_n(px+6)}" y="{_n(py-6)}" fill="{red}" font-family="Times New Roman, serif" font-size="11">{label}</text>')
    nodes.append('</g>');closing=data.rfind(b'</svg>')
    return data[:closing]+''.join(nodes).encode()+data[closing:]


def registry():return json.loads((ASSET_DIR/'source-assets.json').read_text())


def entry(context):
    c=_normalized_content(context);condition=_section(c,'condition')
    assets=[a for a in c.get('assets',[]) if a.get('asset_key')=='image_1' and 'image_1' in (condition or {}).get('asset_keys',[])]
    if len(assets)!=1:raise ContentPlanError('unique image_1 required')
    found=registry()['conditions'].get(assets[0].get('asset_id'))
    if found is None:
        reason=registry().get('unsupported_conditions',{}).get(assets[0].get('asset_id'))
        raise ContentPlanError(reason or 'fractional hyperbola source needs an audited registration')
    return found


def required_assets(context):
    e=entry(context)
    return tuple({'source_asset_id':e[m]['source_asset_id'],'section_id':'solution:1','alt_text':alt} for m,alt in [('points','Три точки гиперболы'),('offset','Отступ от асимптоты гиперболы')])


def build_context_repair_plan(context, *, condition_asset_bytes, current_asset_content_type):
    c=_normalized_content(context);condition=_section(c,'condition');solution=_section(c,'solution');answer=_section(c,'answer')
    if not condition or condition_asset_bytes is None:raise ContentPlanError('condition and graph required')
    if str(current_asset_content_type).split(';')[0].lower()!='image/svg+xml':raise ContentPlanError('fractional hyperbola graph must be SVG')
    e=entry(context)
    if hashlib.sha256(condition_asset_bytes).hexdigest()!=e['sha256']:raise ContentPlanError('source SVG differs from audited registration')
    facts=graph_evidence(condition_asset_bytes);k,a,b,c0=(facts[key] for key in ('k','a','b','c'));x,y=facts['point'];x2,y2=facts['second'];x3,y3=facts['third'];ux,uy=facts['offset']
    # Solve the three-point linear system independently of the asymptotes.
    matrix=[[px,Fraction(1),-py,px*py] for px,py in (facts['point'],facts['second'],facts['third'])]
    for col in range(3):
        pivot=next((i for i in range(col,3) if matrix[i][col]),None)
        if pivot is None:raise ContentPlanError('three-point system is singular')
        matrix[col],matrix[pivot]=matrix[pivot],matrix[col]
        divisor=matrix[col][col];matrix[col]=[v/divisor for v in matrix[col]]
        for i in range(3):
            if i!=col:
                factor=matrix[i][col];matrix[i]=[v-factor*w for v,w in zip(matrix[i],matrix[col])]
    if tuple(r[-1] for r in matrix)!=(k,a,b):raise ContentPlanError('three-point system disagrees with graph')
    soup=BeautifulSoup(condition['html'].replace('\u00ad',''),'html.parser');forms=[str(n['data-inline-latex']).replace(' ','') for n in soup.find_all(attrs={'data-inline-latex':True})]
    question=re.search(r'Найдите\s*(?:коэффициент\s*)?([kabc])\s*\.',soup.get_text(' ',strip=True))
    abc_model=bool(forms and forms[0]==r'f(x)=\frac{ax+b}{x+c}')
    if not forms or forms[0] not in (r'f(x)=\frac{k}{x}+ax+b',r'f(x)=\frac{kx+a}{x+b}',r'f(x)=\frac{ax+b}{x+c}') or not question or forms[1:] not in ([],[question[1]]):
        raise ContentPlanError('unsupported fractional hyperbola question')
    sought=({'a':'k','b':'a','c':'b'}.get(question[1]) if abc_model else question[1])
    if sought not in ('k','a','b'):raise ContentPlanError('unsupported fractional hyperbola coefficient')
    result={'k':k,'a':a,'b':b}[sought]
    images=[];keys=[]
    for req in required_assets(context):
        asset=next((a for a in _normalized_content(context)['assets'] if a.get('asset_id')==req['source_asset_id']),None)
        if asset is None:raise ContentPlanError('required graph annotation is not attached')
        key=asset['asset_key'];aid=asset['asset_id'];keys.append(key)
        images.append(f'<center><img alt="{req["alt_text"]}" data-asset-id="{aid}" data-asset-key="{key}" src="/assets/{aid}"/></center>')
    def signed(v):return ('+' if v>=0 else '-')+latex(abs(v))
    def coefficient(v,name):
        if not name:return latex(v)
        return name if v==1 else '-'+name if v==-1 else latex(v)+name if v else ''
    def expression(terms):
        out=''
        for v,name in terms:
            if not v:continue
            text=coefficient(v,name)
            out+=('+' if out and v>0 else '')+text
        return out or '0'
    def subtract_number(v):return '-'+(latex(v) if v>=0 else '('+latex(v)+')')
    def system(*eq):return r'\begin{cases}'+r'\\'.join(eq)+r'\end{cases}'
    pts=(facts['point'],facts['second'],facts['third'])
    reduced=[]
    linear=[expression(((px,'k'),(Fraction(1),'a'),(-py,'b'))) for px,py in pts]
    from math import gcd
    elimination=''
    for index,(px,py) in enumerate(pts[1:],2):
        ck,cb,rhs=x-px,py-y,x*y-px*py
        divisor=gcd(gcd(abs(ck.numerator),abs(cb.numerator)),abs(rhs.numerator))
        if ck<0:divisor=-divisor
        reduced.append((ck/divisor,cb/divisor,rhs/divisor))
        elimination+=(f'<p>Вычтем {"второе" if index==2 else "третье"} уравнение из первого: '
                      f'{formula("a")} сократится.</p>'
                      +row(rf'({linear[0]})-({linear[index-1]})={latex(x*y)}'+subtract_number(px*py))
                      +row(expression(((ck,'k'),(cb,'b')))+'='+latex(rhs)
                           +r'\iff '+expression(((ck/divisor,'k'),(cb/divisor,'b')))+'='+latex(rhs/divisor)))
    u1,v1,t1=reduced[0];u2,v2,t2=reduced[1]
    equations=[expression(((u,'k'),(v,'b')))+'='+latex(t) for u,v,t in reduced]
    db,rb=v1*u2-v2*u1,t1*u2-t2*u1
    def product(v,w):
        return latex(v)+r'\cdot '+(latex(w) if w>=0 else '('+latex(w)+')')
    if u1==u2:
        db,rb=v1-v2,t1-t2
        cancel='<p>Вычтем второе из полученных уравнений: '+formula('k')+' сократится.</p>'
        cancel_row=rf'({expression(((u1,"k"),(v1,"b")))})-({expression(((u2,"k"),(v2,"b")))})={latex(t1)}'+subtract_number(t2)
    else:
        cancel=(f'<p>Чтобы исключить {formula("k")}, умножим первое уравнение на {formula(latex(u2))}, '
                f'второе — на {formula(latex(u1))} и вычтем второе из первого.</p>')
        cancel_row=rf'{latex(u2)}({expression(((u1,"k"),(v1,"b")))})-({latex(u1)})({expression(((u2,"k"),(v2,"b")))})={product(u2,t1)}-({product(u1,t2)})'
    k_sub=expression(((u2,'k'),(v2*b,'')))+'='+latex(t2)
    a_sub=expression(((x*k,''),(Fraction(1),'a'),(-y*b,'')))+'='+latex(x*y)
    first=(images[0]+f'<p>Подставим три точки {formula(rf"A({latex(x)};{latex(y)})")}, '
           f'{formula(rf"B({latex(x2)};{latex(y2)})")} и {formula(rf"C({latex(x3)};{latex(y3)})")} '
           'в формулу функции.</p>'
           +row(system(*(latex(py)+rf'=\frac{{{expression(((px,"k"),(Fraction(1),"a")))}}}{{{latex(px)}+b}}' for px,py in pts)))
           +'<p>Убираем знаменатели:</p>'
           +row(r'\iff '+system(*(rf'{latex(py)}({latex(px)}+b)={expression(((px,"k"),(Fraction(1),"a")))}' for px,py in pts)))
           +'<p>Раскрываем скобки:</p>'
           +row(r'\iff '+system(*(expression(((px*py,''),(py,'b')))+'='+expression(((px,'k'),(Fraction(1),'a'))) for px,py in pts)))
           +'<p>Переносим слагаемые с неизвестными влево, числа — вправо:</p>'
           +row(r'\iff '+system(*(lhs+'='+latex(px*py) for lhs,(px,py) in zip(linear,pts))))
           +elimination
           +'<p>Получили систему с двумя неизвестными:</p>'+row(system(*equations))
           +cancel+row(cancel_row)+row(coefficient(db,'b')+'='+latex(rb)+r'\iff b='+latex(b))
           +f'<p>Подставим {formula("b="+latex(b))} во второе уравнение:</p>'
           +row(k_sub+r'\iff '+coefficient(u2,'k')+'='+latex(t2-v2*b)+(r'\iff k='+latex(k) if u2!=1 else ''))
           +f'<p>Подставим {formula("k="+latex(k))} и {formula("b="+latex(b))} в первое уравнение исходной системы:</p>'
           +row(a_sub+r'\iff a='+expression(((x*y,''),(-x*k,''),(y*b,'')))+'='+latex(a))
           +row(r'\Rightarrow '+sought+'='+latex(result)))
    alternative=(images[1]+f'<p>Выделим целую часть, чтобы формула была канонической для гиперболы. '
                 f'Для этого прибавим и вычтем {formula("kb")}.</p>'
                 +row(r'f(x)=\frac{kx+a}{x+b}=\frac{kx+kb+a-kb}{x+b}=\frac{k(x+b)+(a-kb)}{x+b}')
                 +'<p>Разделим сумму на знаменатель и сократим первую дробь:</p>'
                 +row(r'f(x)=\frac{k(x+b)}{x+b}+\frac{a-kb}{x+b}=k+\frac{a-kb}{x+b}')
                 +'<p><br/></p>'
                 +'<p>Каноническое уравнение гиперболы — '+formula(r'f(x)=\frac{A}{x+B}+C')+'. А значит, в нашем случае:</p>'
                 +f'<p>{formula("B=b")} — сдвиг по горизонтали. '
                 + (f'Асимптота {formula("x="+latex(-b))}: на {formula(latex(abs(b)))} '+('влево' if b>0 else 'вправо') if b else f'Асимптота {formula("x=0")}: сдвига нет')
                 +f' {formula(r"\Rightarrow B="+latex(b))}.</p>'
                 +f'<p>{formula("C=k")} — сдвиг по вертикали. '
                 + (f'Асимптота {formula("y="+latex(k))}: на {formula(latex(abs(k)))} '+('вверх' if k>0 else 'вниз') if k else f'Асимптота {formula("y=0")}: сдвига нет')
                 +f' {formula(r"\Rightarrow C="+latex(k))}.</p>'
                 +f'<p>{formula("A=a-kb")} — масштаб и знак ветвей. '
                 f'Ветви в {"I и III" if c0>0 else "II и IV"} четвертях относительно асимптот, поэтому {formula("A>0" if c0>0 else "A<0")}.</p>'
                 +f'<p>На {formula(latex(abs(uy-k)))} '+('выше' if uy-k>0 else 'ниже')
                 +' горизонтальной асимптоты отступ от вертикальной асимптоты равен '
                 +formula(latex(abs(ux+b)))+' '+('вправо' if ux+b>0 else 'влево')
                 +' (красный отрезок) '+formula(r'\Rightarrow A='+latex(c0))+'.</p>'
                 +row(rf'f(x)=\frac{{{latex(c0)}}}{{x{signed(b)}}}'+signed(k))
                 + ('<p><br/></p>'+row(r'A=a-kb\Rightarrow a=A+kb')
                    +row('k=C='+latex(k)+r',\qquad b=B='+latex(b))
                    +row('a='+latex(c0)+'+'+(latex(k) if k>=0 else '('+latex(k)+')')+r'\cdot '+(latex(b) if b>=0 else '('+latex(b)+')')
                         +'='+latex(c0)+signed(k*b)+'='+latex(a))
                    if sought=='a' else row(sought+'='+('C' if sought=='k' else 'B')+'='+latex(result))))
    html=f'<section data-content-kind="solution" data-solution-title="Решение">{first}</section><section data-content-kind="solution" data-solution-title="Альтернативное решение">{alternative}</section>'
    if abc_model:
        # Rename only LaTeX variables; commands such as \frac and \begin stay intact.
        symbols={'k':'a','a':'b','b':'c'}
        def renamed_formula(match):
            return 'data-inline-latex="'+re.sub(r'\\(?:begin|end)\{[^}]+\}|\\[A-Za-z]+|[A-Za-z]',lambda token:symbols.get(token[0],token[0]),match[1])+'"'
        html=re.sub(r'data-inline-latex="([^"]*)"',renamed_formula,html)
    old_html=str(solution.get('html') or '') if solution else ''
    retired=set(registry().get('retired_asset_ids',[]))
    retired_keys=tuple(a['asset_key'] for a in _normalized_content(context)['assets'] if a.get('asset_id') in retired)
    # Keep unrelated editorial illustrations.
    for img in re.findall(r'<img\b[^>]*>',old_html,re.I):
        if not any(key in img for key in (*keys,'image_1',*retired_keys)):html+=img
    changes=[];cleaned=condition['html'].replace('\u00ad','').replace(r'f(x)=\frac{k}{x}+ax+b',r'f(x)=\frac{kx+a}{x+b}')
    if cleaned!=condition['html']:changes.append(_section_transformation(condition,'condition','Условие',cleaned,asset_keys=tuple(condition.get('asset_keys',[]))))
    solution_keys=tuple(dict.fromkeys(tuple(key for key in solution.get('asset_keys',[]) if key not in retired_keys) + tuple(keys))) if solution else tuple(keys)
    comparable=lambda v:re.sub(r'\s+data-transformation-target-id="[^"]*"','',v)
    if not solution or comparable(old_html)!=comparable(html) or tuple(solution.get('asset_keys',[]))!=solution_keys:
        changes.append(_section_transformation(solution,'solution','Решение',html,asset_keys=solution_keys))
    value=answer_text(result).replace('.',',');old_answer=BeautifulSoup(str(answer.get('html') or '') if answer else '','html.parser').get_text('',strip=True)
    if old_answer!=value:changes.append(_section_transformation(answer,'answer','Ответ',f'<p><span data-effect="spaced">{value}</span></p>'))
    return RepairPlan(value,tuple(changes))
