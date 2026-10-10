"""Adapt the reviewed source number-line SVG to exact inequality intersections."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import xml.etree.ElementTree as ET

from .linear_system_intervals import Inequality, number, solve

ASSET_KEY = 'generated_inequality_intersection'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
_TEMPLATE = ET.fromstring(Path(__file__).with_name('inequality_number_line_template.svg').read_bytes())
AXIS_Y = 48.581
LEFT = 9.873
RIGHT = 169.496


def render_intersection_svg(rows: tuple[Inequality, ...]) -> bytes:
    """Reuse source axis, arrow and x glyph; adapt boundaries, arcs and hatching."""
    if len(rows) != 2:
        raise ValueError('two solved inequalities are required')
    bounds = sorted({row.bound for row in rows})
    def coordinate(value: Fraction) -> float:
        """Place ordered boundaries at the source's two reviewed marker positions."""
        return 93.006 if len(bounds) == 1 else (66.955 if value == bounds[0] else 119.057)
    def node(tag: str, **attrs: object) -> ET.Element:
        """Append an editable primitive in the source SVG namespace."""
        return ET.SubElement(root, f'{{{NS}}}{tag}', {key.replace('_', '-'):str(value) for key,value in attrs.items()})
    root = ET.Element(f'{{{NS}}}svg', {'width':'174.612', 'height':'52', 'viewBox':'6.311 25 174.612 52',
                                     'data-template-source-asset-id':'d2730267-5298-40ad-b8aa-870fad5f6f7e'})
    node('title').text = 'Пересечение решений двух неравенств'
    node('rect', x='6.311', y='25', width='174.612', height='52', fill='white')
    # Copy the existing asset's axis, arrowhead and outlined italic x exactly.
    for child in _TEMPLATE:
        if (child.tag == f'{{{NS}}}line' and child.get('y1') == str(AXIS_Y)
                or child.tag == f'{{{NS}}}polygon'
                or child.tag == f'{{{NS}}}g' and child.find(f'.//{{{NS}}}clipPath') is not None):
            root.append(deepcopy(child))
    result = solve(rows)
    if not result.empty:
        left = coordinate(result.lower) if result.lower is not None else LEFT
        right = coordinate(result.upper) if result.upper is not None else RIGHT - 5
        # Preserve the reference asset's hatch slope, spacing and blue stroke.
        x = left + .5
        while x + 4.256 <= right:
            node('line', x1=f'{x+4.256:.3f}', y1='43.658', x2=f'{x:.3f}', y2='48.219',
                 fill='none', stroke='#143B8F', stroke_width='.75', stroke_miterlimit='10')
            x += 3.34
    for index,row in enumerate(rows):
        start = coordinate(row.bound)
        end = RIGHT if row.bound_relation.startswith('>') else LEFT
        height = 16.372 if index == 0 else 9.445
        top = AXIS_Y-height
        direction = 1 if end > start else -1
        shoulder = start + direction * min(25.187, abs(end-start)*.45)
        node('path', data_half_line=index+1,
             d=f'M{start:.3f} {AXIS_Y} C{start:.3f} {top:.3f} {shoulder:.3f} {top:.3f} {shoulder:.3f} {top:.3f} H{end}',
             fill='none', stroke='#000000', stroke_width='.75')
        node('path', data_half_line_arrow=index+1,
             d=f'M{end-direction*1.889:.3f} {top-.944:.3f} L{end} {top:.3f} L{end-direction*1.889:.3f} {top+.944:.3f}',
             fill='none', stroke='#000000', stroke_width='.75')
    for index,row in enumerate(rows):
        node('circle', data_inequality=index+1, cx=f'{coordinate(row.bound):.3f}', cy=AXIS_Y,
             r='2.688', fill='#000000' if row.bound_relation.endswith('=') else 'white',
             stroke='#000000', stroke_width='.75')
    # A shared boundary represents the intersection's strictness on the axis.
    if len(bounds) == 1:
        closed = not result.empty and ((result.lower == bounds[0] and result.lower_closed)
                                       or (result.upper == bounds[0] and result.upper_closed))
        node('circle', cx=f'{coordinate(bounds[0]):.3f}', cy=AXIS_Y, r='2.688',
             fill='#000000' if closed else 'white', stroke='#000000', stroke_width='.75')
    for bound in bounds:
        label = number(bound).replace('{,}', ',')
        if r'\frac' in label:
            label = str(bound)
        node('text', x=f'{coordinate(bound):.3f}', y='67.5', text_anchor='middle',
             font_family='Times New Roman,serif', font_size='12', fill='#000000').text=label
    return ET.tostring(root, encoding='utf-8')
