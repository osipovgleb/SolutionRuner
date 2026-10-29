"""Solve quadratic choices and match an independently reviewed condition diagram."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from html import escape
import hashlib
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

RULE = 'quadratic-inequality-graph-choices'
_EVIDENCE = json.loads(Path(__file__).with_name('quadratic_inequality_choices_evidence.json').read_text())
_FORMULA = re.compile(r'x\^2(?:(?P<b>[+-]\d*)x)?(?P<c>[+-]\d+)?(?P<relation><=|>=|<|>)0')


@dataclass(frozen=True)
class QuadraticChoice:
    latex: str
    factorization: str | None
    intervals: tuple[Interval, ...]
    roots: tuple[Fraction, ...]
    square_comparison: str | None = None


def solve_choice(latex: str) -> QuadraticChoice:
    """Accept monic integer quadratics with integral roots and exact endpoints."""
    raw = latex.replace('{', '').replace('}', '').replace(' ', '').replace('−', '-')
    raw = raw.replace(r'\lt', '<').replace(r'\gt', '>')
    for command, relation in ((r'\leqslant', '<='), (r'\geqslant', '>='),
                              (r'\leq', '<='), (r'\geq', '>='), (r'\le', '<='), (r'\ge', '>=')):
        raw = raw.replace(command, relation)
    match = _FORMULA.fullmatch(raw)
    if match is None:
        raise ValueError('unsupported quadratic inequality')
    b_raw = match['b'] or '0'
    b = int(b_raw + '1' if b_raw in ('+', '-') else b_raw)
    c = int(match['c'] or '0')
    negative = match['relation'].startswith('<')
    closed = match['relation'].endswith('=')
    discriminant = b*b - 4*c
    if discriminant < 0:
        comparison = 'x^{2}' + relation_latex(match['relation']) + str(-c) if b == 0 else None
        return QuadraticChoice(latex, None, () if negative else (Interval(),), (), comparison)
    root = isqrt(discriminant)
    if root*root != discriminant or (-b-root) % 2:
        raise ValueError('nonintegral quadratic roots require separate support')
    lower, upper = Fraction(-b-root, 2), Fraction(-b+root, 2)
    def factor(value: Fraction) -> str:
        return 'x' if value == 0 else '(x' + ('-' if value > 0 else '+') + number(abs(value)) + ')'
    factors = factor(lower) + factor(upper)
    if lower == upper:
        result = ((Interval(lower, upper, True, True),) if closed else ()) if negative else (
            (Interval(),) if closed else (Interval(upper=lower), Interval(lower=upper)))
    else:
        result = (Interval(lower, upper, closed, closed),) if negative else (
            Interval(upper=lower, upper_closed=closed), Interval(lower=upper, lower_closed=closed))
    return QuadraticChoice(latex, factors + relation_latex(match['relation']) + '0', result, (lower, upper))


def _condition_options(condition_html: str) -> tuple[tuple[str, ...], str | None]:
    """Restore only the audited legacy x-space-2 notation inside option cells."""
    soup = BeautifulSoup(condition_html, 'html.parser')
    cells = soup.find_all('li') or soup.find_all('nobr')
    if len(cells) != 4:
        raise ValueError('four quadratic options are required')
    options = []
    repaired = False
    for cell in cells:
        formulas = cell.find_all('span', attrs={'data-inline-latex': True})
        if len(formulas) == 1:
            options.append(formulas[0]['data-inline-latex'])
            continue
        if formulas or cell.find('img'):
            raise ValueError('one formula per quadratic option is required')
        text = cell.get_text(' ', strip=True).replace('\xad', '').replace('−', '-')
        if not re.match(r'^x\s+2\s', text):
            raise ValueError('unreviewed plain-text quadratic notation')
        latex = re.sub(r'^x\s+2', 'x^{2}', text).replace(' ', '')
        solve_choice(latex)
        cell.clear()
        formula = soup.new_tag('span', attrs={'data-inline-latex': latex})
        cell.append(formula)
        options.append(latex)
        repaired = True
    return tuple(options), str(soup) if repaired else None


def _verified_choices(context: dict[str, Any]) -> tuple[tuple[QuadraticChoice, ...], str]:
    content = _normalized_content(context)
    condition = _section(content, 'condition')
    evidence = _EVIDENCE.get(str(context.get('problem_id')))
    if evidence is None:
        raise ValueError('condition number line has not been visually reviewed')
    if condition is None or condition_fingerprint(str(condition['html'])) not in {
            evidence['condition_sha256'], evidence.get('repaired_condition_sha256')}:
        raise ValueError('condition changed since visual review')
    soup = BeautifulSoup(condition['html'], 'html.parser')
    images = soup.find_all('img')
    if len(images) != 1 or images[0].get('data-asset-id') != evidence['asset_id']:
        raise ValueError('reviewed condition diagram changed')
    options, repaired_html = _condition_options(condition['html'])
    if repaired_html and condition_fingerprint(repaired_html) != evidence.get('repaired_condition_sha256'):
        raise ValueError('plain-text formula repair has not been reviewed')
    choices = [solve_choice(latex) for latex in options]
    matches = [str(i) for i, choice in enumerate(choices, 1)
               if [list(interval.key()) for interval in choice.intervals] == evidence['intervals']]
    if len(matches) != 1:
        raise ValueError('condition diagram must select exactly one independently solved option')
    return tuple(choices), matches[0]


def _formula(latex: str) -> str:
    return '<p><span data-inline-latex="' + escape(latex, quote=True) + '"></span>.</p>'


def _constant_sign_solution(choice: QuadraticChoice) -> str:
    """Move the positive constant and justify truth from the square's sign."""
    def inline(latex: str) -> str:
        return '<span data-inline-latex="' + escape(latex, quote=True) + '"></span>'
    verdict = 'ист.' if choice.intervals else 'ложь.'
    result = r'\mathbb{R}' if choice.intervals else r'\varnothing'
    return ('<li><p>' + inline(choice.latex + r'\iff ' + choice.square_comparison)
            + ' — ' + verdict + ', т.к. ' + inline(r'x^{2}\ge 0')
            + ' всегда ' + inline(r'\Rightarrow x\in ' + result) + '.</p><br/></li>')


def build_context_repair_plan(context: dict[str, Any], *, generated_solution_assets: tuple[dict[str, str], ...] = ()) -> RepairPlan:
    """Keep the condition; place a diagram and x-membership after every option."""
    choices, expected = _verified_choices(context)
    content = _normalized_content(context)
    solution = _section(content, 'solution')
    answer = _section(content, 'answer')
    assets = {a['asset_key']: a for a in generated_solution_assets}
    keys = [f'generated_quadratic_option_{i}' for i, choice in enumerate(choices, 1)
            if choice.square_comparison is None]
    if generated_solution_assets and (len(generated_solution_assets) != len(keys) or set(assets) != set(keys)):
        raise ValueError('diagrams must match exactly the nontrivial quadratic options')
    changes = []
    condition = _section(content, 'condition')
    _, repaired_html = _condition_options(condition['html'])
    if repaired_html:
        changes.append(_section_transformation(condition, 'condition', 'Условие', repaired_html,
                                               asset_keys=tuple(condition.get('asset_keys') or [])))
    rows = []
    for index, choice in enumerate(choices, 1):
        key = f'generated_quadratic_option_{index}'
        if choice.square_comparison is not None:
            rows.append(_constant_sign_solution(choice))
            if any(a.get('asset_key') == key for a in content.get('assets', [])):
                changes.append({'transformation_target_id':'asset:' + key, 'operation':'remove'})
            continue
        algebra = choice.latex
        if choice.factorization:
            algebra += r'\iff ' + choice.factorization
        explanation = ''
        if choice.factorization is None:
            explanation = '<p>Квадратный трёхчлен положителен при любом действительном значении ' + '<span data-inline-latex="x"></span>.</p>'
        diagram = ''
        if key in assets:
            asset = assets[key]
            alt = f'Множество решений неравенства {index}'
            markup = (f'<img alt="{alt}" data-asset-key="{key}" data-asset-id="{asset["source_asset_id"]}" '
                      f'src="{asset["url"]}"/>')
            diagram = '<center>' + markup + '</center>'
            existing = next((a for a in content.get('assets', []) if a.get('asset_key') == key), None)
            if existing is None or existing.get('asset_id') != asset['source_asset_id']:
                changes.append({'transformation_target_id': 'asset:' + key, 'operation': 'add',
                                'value': {'asset_key': key, 'asset_id': asset['source_asset_id'], 'url': asset['url'],
                                          'html': markup, 'kind': 'ordinary_image', 'alt': alt,
                                          'parent_target_id': 'section:solution:1', 'position': keys.index(key)}})
        result = r'\cup'.join(interval_latex(i) for i in choice.intervals) if choice.intervals else r'\varnothing'
        rows.append('<li>' + _formula(algebra) + explanation + diagram + _formula(r'x\in ' + result) + '<br/></li>')
    html = ('<p>Решим каждое из неравенств:</p><ol data-layout="source-options">' + ''.join(rows)
            + '</ol><p>На рисунке в условии изображено множество решений неравенства '
            + f'<span data-inline-latex="{escape(choices[int(expected)-1].latex, quote=True)}"></span>.</p>')
    if (solution is None or condition_fingerprint(str(solution.get('html') or '')) != condition_fingerprint(html)
            or list(solution.get('asset_keys') or []) != (keys if assets else [])):
        changes.append(_section_transformation(solution, 'solution', 'Решение', html, asset_keys=tuple(keys) if assets else ()))
    current = BeautifulSoup(answer['html'], 'html.parser').get_text('', strip=True) if answer else ''
    if current != expected:
        changes.append(_section_transformation(answer, 'answer', 'Ответ', f'<p><span data-effect="spaced">{expected}</span></p>'))
    return RepairPlan(expected, tuple(changes))


def diagram_specs(context: dict[str, Any]) -> tuple[dict[str, str], ...]:
    """Render all four solved sets only after the input diagram passes review."""
    choices, _ = _verified_choices(context)
    result = []
    for index, choice in enumerate(choices, 1):
        if choice.square_comparison is not None:
            continue
        svg = render_quadratic_sign_chart_svg(choice.roots, choice.intervals)
        result.append({'asset_key': f'generated_quadratic_option_{index}', 'svg_text': svg.decode(),
                       'sha256': hashlib.sha256(svg).hexdigest()})
    return tuple(result)
