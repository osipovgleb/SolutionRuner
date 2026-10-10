"""Complete verified inequality-system conditions, exact choice answers and solutions."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from .inequality_systems import build_context_repair_plan as presentation_plan
from .linear_system_intervals import parse_system, solve, solution_html
from .inequality_systems import condition_fingerprint, _repair_options
from .inequality_system_svg import ASSET_KEY, render_intersection_svg

_CHOICES = json.loads(Path(__file__).with_name('inequality_systems_choices.json').read_text())


@dataclass(frozen=True)
class RepairPlan:
    """Return independently verified choice number and only needed section changes."""

    answer: str
    transformations: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...] = ()


def choices_fingerprint(cells: list[Any]) -> str:
    """Bind option order, visible text, formulas and immutable image identities."""
    values = []
    for cell in cells:
        text = re.sub(r'^\d\)\s*', '', cell.get_text(' ', strip=True).replace('\xad', ''))
        values.append({'text': text, 'images': [tag['data-asset-id'] for tag in cell.find_all('img')],
                       'formulas': [tag['data-inline-latex'] for tag in cell.find_all('span', attrs={'data-inline-latex': True})]})
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def build_context_repair_plan(context: dict[str, Any], *, generated_solution_assets: tuple[dict[str, str], ...] = ()) -> RepairPlan:
    """Solve the system, verify its reviewed option and fill missing or affected content."""
    record = _CHOICES.get(str(context.get('problem_id')))
    if not record or 'choice' not in record:
        raise ValueError(record.get('blocked_reason') if record else 'unreviewed answer choices')
    content = _normalized_content(context)
    condition = _section(content, 'condition')
    answer = _section(content, 'answer')
    solution = _section(content, 'solution')
    if condition is None:
        raise ValueError('condition is required')
    base = presentation_plan(context)
    condition_html = next((t['value']['html'] for t in base.transformations if t['transformation_target_id'].startswith('section:condition')), str(condition['html']))
    soup = BeautifulSoup(condition_html, 'html.parser')
    cells = soup.find_all('td') or soup.find_all('li')
    corrected_layout = False
    if record.get('option_reorder_condition_sha256') == condition_fingerprint(str(condition['html'])):
        if len(cells) != 4 or choices_fingerprint(cells) != record['source_choices_sha256']:
            raise ValueError('reviewed option layout changed')
        cells = sorted(cells, key=lambda cell: int(re.match(r'^(\d)\)', cell.get_text(' ', strip=True)).group(1)))
        contents = [cell.decode_contents() for cell in cells]
        tables = soup.find_all('table')
        markup = ''.join('<table data-layout="media-grid"><tbody><tr>'
                         + ''.join(f'<td>{item}</td>' for item in contents[start:start+2])
                         + '</tr></tbody></table>' for start in (0, 2))
        fragment = BeautifulSoup(markup, 'html.parser')
        for table in list(fragment.contents):
            tables[0].insert_before(table)
        for table in tables:
            table.decompose()
        _repair_options(soup)
        cells = soup.find_all('td')
        corrected_layout = True
    if (len(cells) != 4 or any(not re.match(rf'^{i}\)', cell.get_text(' ', strip=True)) for i, cell in enumerate(cells, 1))
            or choices_fingerprint(cells) != record['choices_sha256']):
        raise ValueError('answer options changed since visual review')
    formulas = [tag['data-inline-latex'] for tag in soup.find_all('span', attrs={'data-inline-latex': True})
                if tag['data-inline-latex'].startswith(r'\begin{cases}')]
    if len(formulas) != 1:
        raise ValueError('exactly one system is required')
    rows = parse_system(formulas[0])
    interval = solve(rows)
    if list(interval.key()) != record['interval']:
        raise ValueError('solved set does not match the visually verified option')
    expected = record['choice']
    current = BeautifulSoup(str(answer.get('html') or ''), 'html.parser').get_text('', strip=True) if answer else ''
    changes = list(base.transformations)
    if corrected_layout:
        condition_html = str(soup)
        keys = tuple(dict.fromkeys(tag['data-asset-key'] for tag in soup.find_all('img', attrs={'data-asset-key': True})))
        changes = [t for t in changes if not t['transformation_target_id'].startswith('section:condition')]
        changes.insert(0, _section_transformation(condition, 'condition', 'Условие', condition_html, asset_keys=keys))
    if current != expected:
        changes.append(_section_transformation(answer, 'answer', 'Ответ', f'<p><span data-effect="spaced">{expected}</span></p>'))
    existing_solution = str(solution.get('html') or '') if solution else ''
    generated = solution_html(formulas[0], rows, interval, expected)
    asset_keys = list(solution.get('asset_keys') or []) if solution and generated == existing_solution else []
    if generated_solution_assets:
        if len(generated_solution_assets) != 1:
            raise ValueError('one intersection diagram is required')
        asset = generated_solution_assets[0]
        if asset['asset_key'] != ASSET_KEY:
            raise ValueError('unexpected generated diagram identity')
        markup = f'<img alt="Пересечение решений двух неравенств" data-asset-key="{ASSET_KEY}" data-asset-id="{asset["source_asset_id"]}" src="{asset["url"]}"/>'
        tree = BeautifulSoup(generated, 'html.parser')
        previous = tree.find('img', attrs={'data-asset-key': ASSET_KEY})
        if previous:
            previous.replace_with(BeautifulSoup(markup, 'html.parser').img)
            generated = str(tree)
        else:
            generated += '<center>' + markup + '</center>'
        asset_keys = list(dict.fromkeys(asset_keys + [ASSET_KEY]))
        existing_asset = next((a for a in content.get('assets', []) if a.get('asset_key') == ASSET_KEY), None)
        if not existing_asset or existing_asset.get('asset_id') != asset['source_asset_id']:
            changes.append({'transformation_target_id': f'asset:{ASSET_KEY}',
                            # The diagram is absent from the immutable source.
                            # Its durable override must remain an add on replay,
                            # including when a new render replaces its asset ID.
                            'operation': 'add',
                            'value': {'asset_key': ASSET_KEY, 'asset_id': asset['source_asset_id'],
                                      'url': asset['url'], 'html': markup, 'kind': 'ordinary_image',
                                      'alt': 'Пересечение решений двух неравенств',
                                      'parent_target_id': 'section:solution:1', 'position': 0}})
    if condition_fingerprint(existing_solution) != condition_fingerprint(generated):
        changes.append(_section_transformation(solution, 'solution', 'Решение', generated, asset_keys=tuple(asset_keys)))
    return RepairPlan(expected, tuple(changes))


def diagram_specs(context: dict[str, Any]) -> tuple[dict[str, str], ...]:
    """Generate SVG only after the equation and all four choices pass verification."""
    plan = build_context_repair_plan(context)
    condition = _section(_normalized_content(context), 'condition')
    raw = next((change['value']['html'] for change in plan.transformations
                if change['transformation_target_id'].startswith('section:condition')), str(condition['html']))
    soup = BeautifulSoup(raw, 'html.parser')
    latex = next(tag['data-inline-latex'] for tag in soup.find_all('span', attrs={'data-inline-latex': True})
                 if tag['data-inline-latex'].startswith(r'\begin{cases}'))
    svg = render_intersection_svg(parse_system(latex))
    return ({'asset_key': ASSET_KEY, 'svg_text': svg.decode(), 'sha256': hashlib.sha256(svg).hexdigest()},)
