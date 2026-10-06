"""Two methods for f(x)=k/x+a; all existing image assets stay untouched."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from html import escape
import hashlib
import re
from typing import Any
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from .diagrams import condition_entry, solution_images, obsolete_solution_asset_keys
from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation


@dataclass(frozen=True)
class RepairPlan:
    answer: str
    transformations: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...] = ()


# Visually audited immutable raster graphs. Pin the bytes, never a task's answer.
# Each tuple is k, a, x, y for f(x)=k/(x+a) and its marked point.
_RASTER_HORIZONTAL = {
    '7d4d5e053ab0c90b6bc03b8263b622890e3c21eae0e49365e38360c93f92b657': (-3, -1, 2, -3),
    'a286961697060596012cedd34d692318fc70022b7f390f3b05de5a334e4657f8': (-5, 2, 3, -1),
}


def number(raw: str) -> Fraction:
    raw = raw.strip().replace('−', '-').replace('{,}', '.').replace(',', '.')
    mixed = re.fullmatch(r'(-?\d+)\\frac\{(\d+)\}\{(\d+)\}', raw)
    if mixed:
        whole, numerator, denominator = map(int, mixed.groups())
        if not denominator:
            raise ContentPlanError('zero denominator')
        return Fraction(whole)+(1 if whole >= 0 else -1)*Fraction(numerator, denominator)
    match = re.fullmatch(r'\\frac\{(-?\d+)\}\{(\d+)\}', raw)
    if match:
        if int(match[2]) == 0:
            raise ContentPlanError('zero denominator')
        return Fraction(int(match[1]), int(match[2]))
    if not re.fullmatch(r'-?\d+(?:\.\d+)?', raw):
        raise ContentPlanError('unsupported numeric argument')
    return Fraction(raw)


def latex(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return ('-' if value < 0 else '') + rf'\frac{{{abs(value.numerator)}}}{{{value.denominator}}}'


def answer_text(value: Fraction) -> str:
    denominator = value.denominator
    for factor in (2, 5):
        while denominator % factor == 0:
            denominator //= factor
    if denominator != 1:
        raise ContentPlanError('answer is not a terminating decimal')
    from decimal import Decimal, localcontext
    with localcontext() as ctx:
        ctx.prec = max(30, len(str(abs(value.numerator))) + len(str(value.denominator)) + 5)
        return format(Decimal(value.numerator) / Decimal(value.denominator), 'f').rstrip('0').rstrip('.') if value.denominator != 1 else str(value.numerator)


def formula(value: str) -> str:
    return f'<span data-inline-latex="{escape(value, quote=True)}"></span>'


def row(value: str) -> str:
    return '<center><p>'+formula(value).replace('data-inline-latex=', 'data-formula-render-mode="display" data-inline-latex=')+'</p></center>'


def horizontal_solution(k: Fraction, a: Fraction, x: Fraction, y: Fraction,
                        target: Fraction, result: Fraction, points_image: str = '', offset_image: str = '',
                        mode: str = 'argument', second_point=None, offset_point=None) -> str:
    x2,y2 = second_point or (-2*a-x,-y)
    ux,uy = offset_point or (x,y)
    if not y or y==y2 or y2*(x2+a)!=k or uy*(ux+a)!=k:
        raise ContentPlanError('horizontal two-point system disagrees with graph')
    def signed(v):return ('+' if v>=0 else '-')+latex(abs(v))
    def coefficient(v):return 'a' if v==1 else '-a' if v==-1 else latex(v)+'a'
    def system(*eq):return r'\begin{cases}'+r'\\'.join(eq)+r'\end{cases}'
    def denominator(v):return latex(v)+signed(a)
    function=rf'f(x)=\frac{{{latex(k)}}}{{x{signed(a)}}}'
    systems=[system(rf'{latex(y)}=\frac{{k}}{{{latex(x)}+a}}',rf'{latex(y2)}=\frac{{k}}{{{latex(x2)}+a}}'),
             system('k='+latex(x*y)+('+' if y>0 else '')+coefficient(y),
                    'k='+latex(x2*y2)+('+' if y2>0 else '')+coefficient(y2)),
             system(coefficient(y-y2)+'='+latex(x2*y2-x*y),
                    'k='+latex(x*y)+('+' if y>0 else '')+coefficient(y)),
             system('a='+latex(a),'k='+latex(k))]
    decimal=answer_text(result).replace('.', '{,}')
    if mode=='value':
        finish=row(rf'f({latex(target)})=\frac{{{latex(k)}}}{{{denominator(target)}}}=\frac{{{latex(k)}}}{{{latex(target+a)}}}={latex(result)}'
                   +('='+decimal if decimal!=latex(result) else ''))
    else:
        finish=row(rf'\frac{{{latex(k)}}}{{x{signed(a)}}}={latex(target)}'
                   +r'\iff '+rf'x{signed(a)}=\frac{{{latex(k)}}}{{{latex(target)}}}={latex(k/target)}'
                   +r'\iff '+rf'x={latex(result)}'+('='+decimal if decimal!=latex(result) else ''))
    shift=f'Так как график сдвинут на {formula(latex(abs(a)))} '+('влево' if a>0 else 'вправо')+f', {formula("a="+signed(a))}.' if a else f'Вертикальная асимптота совпадает с осью ординат, {formula("a=0")}.'
    quadrants='первой и третьей' if k>0 else 'второй и четвёртой'
    return (points_image+f'<p>Возьмём две точки: {formula(rf"A({latex(x)};{latex(y)})")} и '
            f'{formula(rf"B({latex(x2)};{latex(y2)})")}. Подставим их координаты в формулу '
            f'{formula(r"y=\frac{k}{x+a}")}.</p>'
            +row(r'\iff '.join(systems))+row(r'\Rightarrow '+function)+finish
            +'<p><b>Альтернативное решение</b></p>'+offset_image
            +f'<p>{shift}</p>'
            +f'<p>Ветви графика расположены в {quadrants} четвертях относительно асимптот, '
            f'поэтому {formula("k>0" if k>0 else "k<0")}.</p>'
            +f'<p>Возьмём точку на {formula(latex(abs(uy)))} '+('выше' if uy>0 else 'ниже')
            +' горизонтальной асимптоты. Красный горизонтальный отрезок показывает отступ от вертикальной асимптоты: '
            +formula(latex(abs(ux+a)))+' '+('вправо' if ux+a>0 else 'влево')+'. '
            +formula(r'\Rightarrow k='+signed(k))+'.</p>'+row(function)+finish)


def vertical_solution(k: Fraction, a: Fraction, x: Fraction, y: Fraction,
                      target: Fraction, result: Fraction, mode: str, points_image: str = '', offset_image: str = '',
                      second_point=None, offset_point=None) -> str:
    x2, y2 = second_point or (-x, 2*a-y)
    dx, py = offset_point or (x, y)
    dy = py-a
    if x2 == x or k/x2+a != y2 or dx*dy != k:
        raise ContentPlanError('two-point system disagrees with graph evidence')

    def signed(v):
        return ('+' if v >= 0 else '-')+latex(abs(v))

    def coefficient(v):
        if v == 1:
            return 'a'
        if v == -1:
            return '-a'
        return latex(v)+'a'

    def system(*equations):
        return r'\begin{cases}'+r'\\'.join(equations)+r'\end{cases}'

    function = rf'f(x)=\frac{{{latex(k)}}}{{x}}'+signed(a)
    decimal = answer_text(result).replace('.', '{,}')
    if mode == 'value':
        reduced = latex(k/target)
        exact = latex(result)
        calculation = rf'f({latex(target)})=\frac{{{latex(k)}}}{{{latex(target)}}}'+signed(a)+'='+reduced+signed(a)+'='+exact
        if decimal != exact:
            calculation += '='+decimal
        finish = row(calculation)
    else:
        finish = row(rf'\frac{{{latex(k)}}}{{x}}'+signed(a)+'='+latex(target)
                     +r'\iff '+rf'\frac{{{latex(k)}}}{{x}}={latex(target-a)}'
                     +r'\iff '+rf'x=\frac{{{latex(k)}}}{{{latex(target-a)}}}={latex(result)}'
                     + ('='+decimal if decimal != latex(result) else ''))
    systems = [
        system(rf'{latex(y)}=\frac{{k}}{{{latex(x)}}}+a',rf'{latex(y2)}=\frac{{k}}{{{latex(x2)}}}+a'),
        system(latex(x*y)+'=k'+('+' if x>0 else '')+coefficient(x),
               latex(x2*y2)+'=k'+('+' if x2>0 else '')+coefficient(x2)),
        system(latex(x*y-x2*y2)+'='+coefficient(x-x2),
               latex(x2*y2)+'=k'+('+' if x2>0 else '')+coefficient(x2)),
        system('a='+latex(a),'k='+latex(k)),
    ]
    chain = r'\iff '.join(systems)
    shift = (f'Так как график сдвинут на {formula(latex(abs(a)))} '
             f'{"вверх" if a>0 else "вниз"}, {formula("a="+signed(a))}.' if a else
             f'Горизонтальная асимптота совпадает с осью абсцисс, {formula("a=0")}.')
    quadrants = 'первой и третьей' if k>0 else 'второй и четвёртой'
    return (
        points_image + f'<p>Возьмём на графике две точки: {formula(rf"A({latex(x)};{latex(y)})")} и '
        f'{formula(rf"B({latex(x2)};{latex(y2)})")}. Подставим их координаты в формулу '
        f'{formula(r"y=\frac{k}{x}+a")}.</p>' + row(chain)
        + row(r'\Rightarrow '+function) + finish
        + '<p><b>Альтернативное решение</b></p>' + offset_image
        + f'<p>{shift}</p>'
        + f'<p>Ветви графика расположены в {quadrants} четвертях относительно асимптот, '
        f'поэтому {formula("k>0" if k>0 else "k<0")}.</p>'
        + f'<p>Возьмём точку на {formula(latex(abs(dy)))} '
        f'{"выше" if dy > 0 else "ниже"} горизонтальной асимптоты. '
        f'Красный горизонтальный отрезок показывает отступ от оси ординат: '
        f'{formula(latex(abs(dx)))} {"вправо" if dx>0 else "влево"}. '
        f'{formula(r"\Rightarrow k="+signed(k))}.</p>'
        + row(function) + finish
    )


def shift_description(a: Fraction, *, horizontal: bool) -> str:
    base = formula(r'y=rac{k}{x}')
    if not a:
        return f'График {base} не сдвинут, его асимптоты совпадают с осями координат.'
    direction = ('влево' if a > 0 else 'вправо') if horizontal else ('вверх' if a > 0 else 'вниз')
    return f'График {base} сдвинут на {formula(latex(abs(a)))} по {"горизонтали" if horizontal else "вертикали"} {direction}.'


def offset_description(dx: Fraction, dy: Fraction) -> str:
    return (
        f'Красный горизонтальный отрезок показывает отступ {formula(latex(abs(dx)))} от вертикальной асимптоты '
        f'{"вправо" if dx > 0 else "влево"}, поэтому {formula("X="+latex(dx))}. '
        f'От горизонтальной асимптоты точка отстоит на {formula(latex(abs(dy)))} '
        f'{"вверх" if dy > 0 else "вниз"}, поэтому {formula("Y="+latex(dy))}.'
    )


def _snap(value: float) -> Fraction:
    if abs(value - round(value)) > .06:
        raise ContentPlanError('graph coordinate is not an unambiguous grid node')
    return Fraction(round(value))


def graph_facts(data: bytes, *, horizontal_model: bool = False) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ContentPlanError('invalid condition SVG') from exc
    if any(node.get('transform') and not node.tag.endswith('image') for node in root.iter()):
        raise ContentPlanError('transformed SVG coordinates are unsupported')
    lines = list(root.iter('{http://www.w3.org/2000/svg}line'))
    def horizontal(node):
        return abs(float(node.get('y1', 0)) - float(node.get('y2', 0))) < .01
    def vertical(node):
        return abs(float(node.get('x1', 0)) - float(node.get('x2', 0))) < .01
    grid = [n for n in lines if n.get('stroke', '').upper() == '#ADAAAA']
    xs = sorted(set(float(n.get('x1')) for n in grid if vertical(n)))
    ys = sorted(set(float(n.get('y1')) for n in grid if horizontal(n)))
    def spacing(values):
        if len(values) < 4:
            raise ContentPlanError('coordinate grid is unavailable')
        gaps = [b-a for a,b in zip(values, values[1:]) if b-a > 1]
        step = sorted(gaps)[len(gaps)//2]
        if any(abs(gap/step-round(gap/step)) > .025 for gap in gaps):
            raise ContentPlanError('coordinate grid is not uniform')
        return step
    sx, sy = spacing(xs), spacing(ys)
    black = [n for n in lines if n.get('stroke', '').upper() in {'#000000', '#0D0F0F'} and not n.get('stroke-dasharray')]
    hx = [n for n in black if horizontal(n) and abs(float(n.get('x2'))-float(n.get('x1'))) > 3*sx]
    vy = [n for n in black if vertical(n) and abs(float(n.get('y2'))-float(n.get('y1'))) > 3*sy]
    asymptotes = [n for n in lines if (vertical(n) if horizontal_model else horizontal(n)) and n.get('stroke-dasharray')]
    asymptote_positions = set(round(float(n.get('x1' if horizontal_model else 'y1')), 3) for n in asymptotes)
    points = [n for n in root.iter('{http://www.w3.org/2000/svg}circle') if n.get('fill', '').upper() == '#143B8F']
    if len(hx) != 1 or len(vy) != 1 or len(asymptote_positions) != 1 or len(points) != 1:
        raise ContentPlanError('need unique axes, horizontal asymptote and marked point')
    ox, oy = float(vy[0].get('x1')), float(hx[0].get('y1'))
    a = _snap((ox-float(asymptotes[0].get('x1')))/sx) if horizontal_model else _snap((oy-float(asymptotes[0].get('y1')))/sy)
    x = _snap((float(points[0].get('cx'))-ox)/sx)
    y = _snap((oy-float(points[0].get('cy')))/sy)
    k = (x+a)*y if horizontal_model else x*(y-a)
    if (x+a if horizontal_model else x) == 0 or k == 0:
        raise ContentPlanError('degenerate hyperbola')
    return k, a, x, y


def legacy_facts(solution: dict[str, Any] | None):
    """For raster only, recover given graph evidence from the saved source solution."""
    soup = BeautifulSoup(str(solution.get('html') or '') if solution else '', 'html.parser')
    for span in soup.find_all(attrs={'data-inline-latex': True}):
        raw = str(span['data-inline-latex']).replace(' ', '').replace('−', '-')
        m = re.fullmatch(r'\\frac\{k\}\{(-?\d+)\}([+-]\d+)=(-?\d+)\\iff\s*k=(-?\d+)', raw)
        if m:
            x, a, y, k = map(Fraction, m.groups())
            if x and k and x*(y-a) == k:
                return k, a, x, y
        m = re.fullmatch(r'k=(-?\d+)-\((-?\d+)\)\\cdot\((-?\d+)\)=(-?\d+)', raw)
        if m:
            xy, x, a, k = map(Fraction, m.groups())
            if x and k and xy-x*a == k:
                return k, a, x, xy/x
        m = re.fullmatch(r'k=(-?\d+)\\cdot\\bigl\((-?\d+)-\((-?\d+)\)\\bigr\)=(-?\d+)', raw)
        if m:
            x, y, a, k = map(Fraction, m.groups())
            if x and k and x*(y-a) == k:
                return k, a, x, y
    raw_formulas = [str(n['data-inline-latex']) for n in soup.find_all(attrs={'data-inline-latex':True})]
    point = next((re.fullmatch(r'A\((-?\d+);(-?\d+)\)', raw) for raw in raw_formulas if raw.startswith('A(')), None)
    for raw in raw_formulas:
        parameters = re.search(r'\\begin\{cases\}a=(-?\d+)\\\\k=(-?\d+)\\end\{cases\}',raw)
        if point and parameters:
            x,y = map(Fraction,point.groups());a,k = map(Fraction,parameters.groups())
            if x and k and k/x+a == y:
                return k,a,x,y
    raise ContentPlanError('raster graph has no verified numerical evidence in the saved solution')


def build_context_repair_plan(context: dict[str, Any], *, condition_asset_bytes: bytes | None,
                              current_asset_content_type: str | None, mode: str, horizontal_model: bool = False) -> RepairPlan:
    content = _normalized_content(context)
    condition, solution, answer = (_section(content, key) for key in ('condition', 'solution', 'answer'))
    if condition is None or condition_asset_bytes is None:
        raise ContentPlanError('condition and its current graph are required')
    soup = BeautifulSoup(str(condition.get('html') or '').replace('\u00ad', ''), 'html.parser')
    forms = [str(n['data-inline-latex']) for n in soup.find_all(attrs={'data-inline-latex': True})]
    if not forms:
        forms = re.findall(r'\$([^$]+)\$', soup.get_text(' ', strip=True))
    forms = [f.replace(' ', '').replace(r'\left', '').replace(r'\right', '').replace(r'\dfrac', r'\frac') for f in forms]
    horizontal = horizontal_model or bool(forms and forms[0] == r'f(x)=\frac{k}{x+a}')
    if not forms or forms[0] not in {r'f(x)=\frac{k}{x}+a', r'f(x)=\frac{k}{x+a}'}:
        raise ContentPlanError('condition is not a supported shifted hyperbola')
    text = soup.get_text(' ', strip=True).replace('−', '-')
    if mode == 'value':
        m = re.fullmatch(r'f\((.+)\)', forms[1]) if len(forms) == 2 else None
        if not m or not re.search(r'Найдите\s*\.', text):
            raise ContentPlanError('unsupported function-value question')
        target = number(m[1])
    elif mode == 'argument':
        if horizontal:
            m = re.fullmatch(r'f\(x\)=(.+)', forms[-1])
            if len(forms) not in (2,3) or (len(forms)==3 and forms[1]!='x') or not m or not re.search(r'Найдите значение.*при котором', text):
                raise ContentPlanError('unsupported horizontal inverse-function question')
        else:
            m = re.search(r'Найдите, при каком значении\s+x\s+значение функции равно\s+(-?\d+(?:[,.]\d+)?)\.', text)
            if len(forms) != 1 or not m:
                raise ContentPlanError('unsupported inverse-function question')
        target = number(m[1])
    else:
        raise ContentPlanError('unknown hyperbola question mode')
    warnings = ()
    if horizontal and str(current_asset_content_type).split(';')[0].lower() == 'image/svg+xml':
        k,a,x,y = graph_facts(condition_asset_bytes, horizontal_model=True)
    elif horizontal:
        facts = _RASTER_HORIZONTAL.get(hashlib.sha256(condition_asset_bytes).hexdigest())
        if facts is None:
            raise ContentPlanError('horizontal graph bytes have no audited numerical evidence')
        k, a, x, y = map(Fraction, facts)
        warnings = ('Изображение условия не SVG; сохранено без изменений. Координаты проверены по исходному растру, закреплённому SHA-256.',)
    elif str(current_asset_content_type).split(';')[0].lower() == 'image/svg+xml':
        k, a, x, y = graph_facts(condition_asset_bytes)
    else:
        warnings = ('Изображение условия не SVG; сохранено без изменений. Числа взяты из проверенной подстановки исходного решения.',)
        k, a, x, y = legacy_facts(solution)
    if (mode == 'value' and target == (-a if horizontal else 0)) or (mode == 'argument' and target == (0 if horizontal else a)):
        raise ContentPlanError('requested value is outside the function domain/range')
    result = (k/(target+a) if mode=='value' else k/target-a) if horizontal else k/target+a if mode == 'value' else k/(target-a)
    entry = condition_entry(context)
    if (entry['kind'] != ('h' if horizontal else 'v') or
            tuple(map(Fraction, entry['facts'])) != (k,a,x,y) or
            entry['sha256'] != hashlib.sha256(condition_asset_bytes).hexdigest()):
        raise ContentPlanError('registered solution graph differs from condition evidence')
    if horizontal and not entry.get('has_overlay') and str(current_asset_content_type).split(';')[0].lower()=='image/svg+xml':
        warnings += ('Исходный SVG содержит внешнюю растровую ссылку; сохранён без изменений, без красных отметок.',)
    points_image, offset_image, diagram_keys = solution_images(context)
    html = (horizontal_solution(k, a, x, y, target, result, points_image, offset_image, mode,
                                tuple(map(Fraction, entry["second_point"])) if entry.get("second_point") else None,
                                tuple(map(Fraction, entry["offset_point"])) if entry.get("offset_point") else None) if horizontal else
            vertical_solution(k, a, x, y, target, result, mode, points_image, offset_image,
                              tuple(map(Fraction, entry["second_point"])) if entry.get("second_point") else None,
                              tuple(map(Fraction, entry["offset_point"])) if entry.get("offset_point") else None))
    retired_keys = obsolete_solution_asset_keys(context)
    if not entry.get('has_overlay'):
        html = html.replace('Красный горизонтальный отрезок показывает отступ', 'На исходном рисунке горизонтальный отступ равен')
    superseded_keys = (*retired_keys, 'image_1') if entry.get('has_overlay') else retired_keys
    # Preserve unrelated illustrations; replace earlier uses of the unannotated condition graph.
    images = [tag for tag in re.findall(r'<img\b[^>]*>', str(solution.get('html') or '') if solution else '', re.IGNORECASE)
              if not any(key in tag for key in (*diagram_keys, *superseded_keys))]
    if images:
        html += ''.join(images)
    first, alternative = html.split('<p><b>Альтернативное решение</b></p>')
    html = (f'<section data-content-kind="solution" data-solution-title="Решение">{first}</section>'
            f'<section data-content-kind="solution" data-solution-title="Альтернативное решение">{alternative}</section>')
    changes = []
    # Only remove soft hyphens from prose; never rewrite image markup or assets.
    condition_html = str(condition.get('html') or '')
    cleaned = condition_html.replace('\u00ad', '')
    if horizontal_model:
        cleaned = cleaned.replace(r'f(x)=\frac{k}{x}+a', r'f(x)=\frac{k}{x+a}')
    if horizontal:
        cleaned = re.sub(r'\$([^$]+)\$', lambda m: formula(m[1].strip()), cleaned)
    if cleaned != condition_html:
        changes.append(_section_transformation(condition, 'condition', 'Условие', cleaned,
                                                asset_keys=tuple(condition.get('asset_keys') or ())))
    solution_keys = tuple(dict.fromkeys(tuple(key for key in (solution.get('asset_keys') or ()) if key not in retired_keys) + diagram_keys)) if solution else diagram_keys
    def comparable(value: str) -> str:
        # Transformation-context annotations are transport metadata, not prose.
        return re.sub(r'\s+data-transformation-target-id="[^"]*"', '', value)
    if (solution is None or comparable(str(solution.get('html') or '')) != comparable(html)
            or tuple(solution.get('asset_keys') or ()) != solution_keys):
        changes.append(_section_transformation(solution, 'solution', 'Решение', html,
                                                asset_keys=solution_keys))
    result_text = answer_text(result).replace('.', ',')
    existing = BeautifulSoup(str(answer.get('html') or '') if answer else '', 'html.parser').get_text('', strip=True)
    if existing.replace('−', '-') != result_text:
        if existing:
            warnings += (f'Исходный ответ {existing} отличается от вычисленного {result_text}; ответ исправляется по графику.',)
        changes.append(_section_transformation(answer, 'answer', 'Ответ', f'<p><span data-effect="spaced">{result_text}</span></p>'))
    return RepairPlan(result_text, tuple(changes), warnings)
