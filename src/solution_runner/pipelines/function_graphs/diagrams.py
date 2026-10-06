"""Solution annotations on original graphs; never redraw the source geometry."""
from __future__ import annotations
from fractions import Fraction
from html import escape
import json
from pathlib import Path

from ..core.errors import ContentPlanError

ASSET_DIR = Path(__file__).parent / 'assets/hyperbolas'


def graph_key(kind: str, facts) -> str:
    return kind + '-' + '-'.join(str(v).replace('-', 'm').replace('/', 'd') for v in facts)


def registry() -> dict:
    path = ASSET_DIR / 'source-assets.json'
    return json.loads(path.read_text()) if path.exists() else {'conditions':{}, 'graphs':{}}


def condition_entry(context: dict) -> dict:
    content = context.get('normalized_content') or {}
    conditions = [s for s in content.get('sections', []) if s.get('key') == 'condition']
    if len(conditions) != 1:
        raise ContentPlanError('unique graph condition required')
    keys = conditions[0].get('asset_keys', [])
    assets = [a for a in content.get('assets', []) if a.get('asset_key') in keys and a.get('asset_key') == 'image_1']
    if len(assets) != 1:
        raise ContentPlanError('unique condition image_1 required')
    entry = registry()['conditions'].get(assets[0].get('asset_id'))
    if entry is None:
        raise ContentPlanError('condition graph needs an audited diagram registration')
    return entry


def required_assets(context: dict) -> tuple[dict[str, str], ...]:
    entry = condition_entry(context)
    graph = registry()['graphs'][entry['graph_key']]
    return tuple({'source_asset_id':graph[method]['source_asset_id'],
                  'section_id':'solution:1', 'alt_text':alt if entry.get('has_overlay') else 'Исходный график функции'}
                 for method, alt in [('points','Две красные точки для подстановки в формулу гиперболы'),
                                     ('offset','Красный горизонтальный отрезок и отступ от асимптоты для вычисления k')])


def solution_images(context: dict) -> tuple[str, str, tuple[str, ...]]:
    assets = (context.get('normalized_content') or {}).get('assets', [])
    images, keys = [], []
    for req in required_assets(context):
        matches = [a for a in assets if a.get('asset_id') == req['source_asset_id']]
        if len(matches) != 1:
            raise ContentPlanError('required hyperbola solution SVG is not attached')
        asset = matches[0]
        key, asset_id = str(asset['asset_key']), str(asset['asset_id'])
        images.append(f'<center><img alt="{escape(req["alt_text"], quote=True)}" data-asset-id="{asset_id}" data-asset-key="{key}" src="/assets/{asset_id}"/></center>')
        keys.append(key)
    return images[0], images[1], tuple(keys)


def _n(value: float) -> str:
    return f'{value:.4f}'.rstrip('0').rstrip('.')


def svg_frame(source: bytes) -> tuple[float, float, float, float, tuple[float, float, float, float]]:
    """Read the original coordinate frame without serializing or changing it."""
    from statistics import median
    from xml.etree import ElementTree as ET
    root = ET.fromstring(source)
    if any(node.get('transform') and not node.tag.endswith('image') for node in root.iter()):
        raise ContentPlanError('transformed source SVG requires an audited overlay frame')
    lines = list(root.iter('{http://www.w3.org/2000/svg}line'))
    def horizontal(node):
        return abs(float(node.get('y1', 0))-float(node.get('y2', 0))) < .01
    def vertical(node):
        return abs(float(node.get('x1', 0))-float(node.get('x2', 0))) < .01
    grid = [n for n in lines if n.get('stroke', '').upper() == '#ADAAAA']
    xs = sorted({float(n.get('x1')) for n in grid if vertical(n)})
    ys = sorted({float(n.get('y1')) for n in grid if horizontal(n)})
    def step(values):
        gaps = [b-a for a,b in zip(values,values[1:]) if b-a > 1]
        if len(gaps) < 3:
            raise ContentPlanError('source SVG grid is unavailable')
        size = median(gaps)
        if any(abs(gap/size-round(gap/size)) > .025 for gap in gaps):
            raise ContentPlanError('source SVG grid is ambiguous')
        return size
    sx,sy = step(xs),step(ys)
    black = [n for n in lines if n.get('stroke','').upper() in {'#000000','#0D0F0F'} and not n.get('stroke-dasharray')]
    hx = [n for n in black if horizontal(n) and abs(float(n.get('x2'))-float(n.get('x1'))) > 3*sx]
    vy = [n for n in black if vertical(n) and abs(float(n.get('y2'))-float(n.get('y1'))) > 3*sy]
    if len(hx)!=1 or len(vy)!=1:
        raise ContentPlanError('source SVG axes are ambiguous')
    view = tuple(map(float,root.get('viewBox','').split()))
    if len(view)!=4:
        raise ContentPlanError('source SVG viewBox is required')
    return float(vy[0].get('x1')),float(hx[0].get('y1')),sx,sy,view


def annotation_points(source: bytes, facts, kind: str = 'v') -> tuple[tuple[Fraction,Fraction],tuple[Fraction,Fraction]]:
    """Pick visible lattice points; never enlarge or reconstruct the source."""
    import math
    k,a,x,y=map(Fraction,facts)
    ox,oy,sx,sy,view=svg_frame(source)
    def inside(point):
        px,py=ox+float(point[0])*sx,oy-float(point[1])*sy
        return view[0]+3<px<view[0]+view[2]-3 and view[1]+3<py<view[1]+view[3]-3
    second=(-2*a-x,-y) if kind=='h' else (-x,2*a-y)
    if not inside(second):
        candidates=[]
        lo=math.floor((view[0]-ox)/sx);hi=math.ceil((view[0]+view[2]-ox)/sx)
        for nx in range(lo,hi+1):
            if (nx+a if kind=='h' else nx)==0 or nx==x:continue
            ny=k/(nx+a) if kind=='h' else k/nx+a
            if ny.denominator==1 and inside((Fraction(nx),ny)):
                candidates.append((Fraction(nx),ny))
        if not candidates:raise ContentPlanError('original image has no second visible lattice point')
        second=min(candidates,key=lambda p:(abs(p[0]),abs(p[1])))
    units=[(k-a,Fraction(1)),(-k-a,Fraction(-1))] if kind=='h' else [(k,a+1),(-k,a-1)]
    offset=next((point for point in units if inside(point)),(x,y))
    return second,offset


def overlay_source_svg(source: bytes, facts, method: str, kind: str = 'v') -> bytes:
    """Append only a red annotation group; retain every original byte/node."""
    from xml.etree import ElementTree as ET
    if method not in {'points','offset'}:
        raise ValueError('unknown graph annotation')
    k,a,x,y=map(Fraction,facts)
    ox,oy,sx,sy,view=svg_frame(source)
    root=ET.fromstring(source)
    markers=[n for n in root.iter('{http://www.w3.org/2000/svg}circle') if n.get('fill','').upper()=='#143B8F']
    if len(markers)!=1:
        raise ContentPlanError('source SVG needs one marked point')
    ax,ay=float(markers[0].get('cx')),float(markers[0].get('cy'))
    if abs((ax-ox)/sx-float(x)) > .06 or abs((oy-ay)/sy-float(y)) > .06:
        raise ContentPlanError('source marker disagrees with overlay evidence')
    (x2,y2),(ux,uy)=annotation_points(source,facts,kind)
    bx,by=ox+float(x2)*sx,oy-float(y2)*sy
    red='#D12626'
    radius=float(markers[0].get('r','2.3'))+.5
    nodes=['<g data-role="hyperbola-solution-overlay">']
    if method=='offset':
        upx,upy=ox+float(ux)*sx,oy-float(uy)*sy
        offset_origin=ox-float(a)*sx if kind=='h' else ox
        nodes.append(f'<line data-role="horizontal-offset" x1="{_n(offset_origin)}" y1="{_n(upy)}" x2="{_n(upx)}" y2="{_n(upy)}" stroke="{red}" stroke-width="1.8"/>')
        points=[('',upx,upy)]
    else:
        points=[('A',ax,ay),('B',bx,by)]
    for label,px,py in points:
        if not (view[0]<px<view[0]+view[2] and view[1]<py<view[1]+view[3]):
            raise ContentPlanError('selected point is outside the original image; do not change its viewBox')
        tx=px+(6 if px>=ox else -6)
        nodes.append(f'<circle data-role="solution-point" cx="{_n(px)}" cy="{_n(py)}" r="{_n(radius)}" fill="{red}"/>')
        if label:
            nodes.append(f'<text x="{_n(tx)}" y="{_n(py-6)}" fill="{red}" font-family="Times New Roman, serif" font-size="11" text-anchor="{"start" if px>=ox else "end"}">{label}</text>')
    nodes.append('</g>')
    closing=source.rfind(b'</svg>')
    if closing < 0:
        raise ContentPlanError('source SVG closing tag is unavailable')
    return source[:closing]+'\n'.join(nodes).encode()+source[closing:]


def obsolete_solution_asset_keys(context: dict) -> tuple[str,...]:
    retired=set(registry().get('retired_asset_ids',[]))
    return tuple(str(a['asset_key']) for a in (context.get('normalized_content') or {}).get('assets',[])
                 if a.get('asset_id') in retired and a.get('asset_key'))
