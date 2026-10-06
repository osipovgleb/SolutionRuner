"""One unknown in f(x)=k/x, with original graph assets preserved."""
from fractions import Fraction
from pathlib import Path
from html import escape
from xml.etree import ElementTree as ET
import hashlib,json,re
from bs4 import BeautifulSoup
from ..core.errors import ContentPlanError
from ..triangles.isosceles.planner import _normalized_content,_section,_section_transformation
from .diagrams import svg_frame,_n
from .hyperbola import RepairPlan,formula,row,latex,number,answer_text,_snap

ASSET_DIR=Path(__file__).parent/'assets/unshifted-hyperbolas'
def registry():return json.loads((ASSET_DIR/'source-assets.json').read_text())
def entry(context):
    content=_normalized_content(context);condition=_section(content,'condition')
    assets=[a for a in content['assets'] if a['asset_key']=='image_1' and a['asset_key'] in condition['asset_keys']]
    if len(assets)!=1:raise ContentPlanError('unique original graph required')
    e=registry()['conditions'].get(assets[0]['asset_id'])
    if not e:raise ContentPlanError('original graph needs audited registration')
    return e,assets[0]
def required_assets(context):
    e,_=entry(context)
    if e['content_type']!='image/svg+xml':return ()
    return tuple({'source_asset_id':e[m]['source_asset_id'],'section_id':'solution:1','alt_text':alt} for m,alt in [('points','Красная точка для подстановки'),('offset','Красный отступ на высоте y=1')])
def annotate(data,e,method):
    if method not in ('points','offset'):raise ValueError(method)
    ox,oy,sx,sy,view=svg_frame(data);x,y=map(Fraction,e['point']);px,py=map(float,e['marker_center'])
    if _snap((px-ox)/sx)!=x or _snap((oy-py)/sy)!=y:raise ContentPlanError('audited point disagrees with original coordinate frame')
    if y!=1:raise ContentPlanError('unit-height offset required')
    nodes=['<g data-role="unshifted-hyperbola-overlay">']
    if method=='offset':nodes.append(f'<line x1="{_n(ox)}" y1="{_n(py)}" x2="{_n(px)}" y2="{_n(py)}" stroke="#D12626" stroke-width="1.8"/>')
    nodes.append(f'<circle cx="{_n(px)}" cy="{_n(py)}" r="2.838" fill="#D12626"/>')
    if method=='points':nodes.append(f'<text x="{_n(px+6)}" y="{_n(py-6)}" fill="#D12626" font-family="Times New Roman, serif" font-size="11">A</text>')
    nodes.append('</g>');i=data.rfind(b'</svg>');return data[:i]+''.join(nodes).encode()+data[i:]
def build_context_repair_plan(context,*,condition_asset_bytes,current_asset_content_type):
    c=_normalized_content(context);condition=_section(c,'condition');solution=_section(c,'solution');answer=_section(c,'answer');e,original=entry(context)
    if not condition_asset_bytes or hashlib.sha256(condition_asset_bytes).hexdigest()!=e['sha256']:raise ContentPlanError('original graph bytes differ from audited registration')
    if current_asset_content_type.split(';')[0]!=e['content_type']:raise ContentPlanError('original graph MIME differs from registration')
    soup=BeautifulSoup(condition['html'].replace('\u00ad',''),'html.parser');forms=[n['data-inline-latex'].replace(' ','') for n in soup.select('[data-inline-latex]')]
    text=soup.get_text(' ',strip=True).replace('\u202f',' ')
    question=re.search(r'Найдите\s*f\s*\(\s*(-?\d+)\s*\)\s*\.',text)
    if forms!=[r'f(x)=\frac{k}{x}'] or not question:raise ContentPlanError('unsupported unshifted hyperbola question')
    target=number(question[1]);x,y=map(Fraction,e['point']);k=x*y
    if not target or not x or y!=1:raise ContentPlanError('nonzero argument and audited unit-height point required')
    result=k/target;decimal=answer_text(result).replace('.','{,}');keys=[];images=[]
    for req in required_assets(context):
        asset=next((a for a in c['assets'] if a['asset_id']==req['source_asset_id']),None)
        if asset is None:raise ContentPlanError('annotated source graph is not attached')
        keys.append(asset['asset_key']);images.append(f'<center><img alt="{escape(req["alt_text"],quote=True)}" data-asset-id="{asset["asset_id"]}" data-asset-key="{asset["asset_key"]}" src="/assets/{asset["asset_id"]}"/></center>')
    if not images:
        keys=[original['asset_key']];img=f'<center><img alt="Исходный график функции" data-asset-id="{original["asset_id"]}" data-asset-key="{original["asset_key"]}" src="/assets/{original["asset_id"]}"/></center>';images=[img,img]
    quotient=rf'\frac{{{latex(k)}}}{{{latex(target)}}}'
    finish=row(rf'f({latex(target)})='+quotient+('='+latex(result) if quotient!=latex(result) else '')+('='+decimal if decimal!=latex(result) else ''))
    first=images[0]+f'<p>Возьмём точку {formula("A("+latex(x)+";"+latex(y)+")")}. Подставим её координаты в {formula(r"y=\frac{k}{x}")}:</p>'+row(rf'{latex(y)}=\frac{{k}}{{{latex(x)}}}\Rightarrow k={latex(k)}')+row(rf'f(x)=\frac{{{latex(k)}}}{{x}}')+finish
    alternative=images[1]+f'<p>Ветви графика находятся в {"первой и третьей" if k>0 else "второй и четвёртой"} четвертях, поэтому {formula("k>0" if k>0 else "k<0")}.</p>'
    alternative+=f'<p>На высоте {formula("y=1")} отступ от оси ординат равен {formula(latex(abs(x)))} {"вправо" if x>0 else "влево"}' + (' (красный отрезок)' if e['content_type']=='image/svg+xml' else '')+f' {formula(r"\Rightarrow k="+latex(k))}.</p>'+row(rf'f(x)=\frac{{{latex(k)}}}{{x}}')+finish
    html=f'<section data-content-kind="solution" data-solution-title="Решение">{first}</section><section data-content-kind="solution" data-solution-title="Альтернативное решение">{alternative}</section>'
    changes=[];old=solution['html'] if solution else '';clean=lambda v:re.sub(r'\s+data-transformation-target-id="[^"]*"','',v)
    retired_keys={a['asset_key'] for a in c['assets'] if a['asset_id'] in registry().get('retired_asset_ids',[])}
    available_keys={a['asset_key'] for a in c['assets']}
    solution_keys=tuple(dict.fromkeys((tuple(key for key in solution.get('asset_keys',[]) if key not in retired_keys and key in available_keys) if solution else ())+tuple(keys)))
    if not solution or clean(old)!=clean(html) or tuple(solution.get('asset_keys',[]))!=solution_keys:changes.append(_section_transformation(solution,'solution','Решение',html,asset_keys=solution_keys))
    value=answer_text(result).replace('.',',');old_answer=BeautifulSoup(answer['html'] if answer else '','html.parser').get_text('',strip=True)
    if old_answer!=value:changes.append(_section_transformation(answer,'answer','Ответ',f'<p><span data-effect="spaced">{value}</span></p>'))
    warnings=() if e['content_type']=='image/svg+xml' else ('condition graph is PNG; original image preserved, red SVG annotations unavailable',)
    return RepairPlan(value,tuple(changes),warnings)
