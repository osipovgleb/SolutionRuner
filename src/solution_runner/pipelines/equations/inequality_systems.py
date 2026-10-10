"""Repair reviewed inequality systems and four-choice layouts without changing answers."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation

_EVIDENCE = json.loads(Path(__file__).with_name('inequality_systems_evidence.json').read_text())


@dataclass(frozen=True)
class RepairPlan:
    """Preserve the source answer and return condition-only transformations."""

    answer: str
    transformations: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...] = ()


def condition_fingerprint(raw: str) -> str:
    """Hash current HTML while ignoring MCP's transient target annotations."""
    soup = BeautifulSoup(raw, 'html.parser')
    for tag in soup.find_all(True):
        tag.attrs.pop('data-transformation-target-id', None)
    return hashlib.sha256(str(soup).encode()).hexdigest()


def _plain(node: Any) -> str:
    """Normalize source typography for exact labels and source-system checks."""
    return re.sub(r'\s+', ' ', node.get_text(' ', strip=True).replace('\xad', '')).strip()


def _repair_system(soup: BeautifulSoup, record: dict[str, Any]) -> None:
    """Replace only a reviewed equation node, retaining all answer-choice assets."""
    latex = record['latex']
    existing = soup.find('span', attrs={'data-inline-latex': latex})
    if existing is not None:
        if record['kind'] == 'raster':
            for image in soup.find_all('img', attrs={'data-asset-id': record['asset_id']}):
                image.decompose()
        return
    replacement = BeautifulSoup('<span></span>', 'html.parser').span
    assert replacement is not None
    replacement['data-inline-latex'] = latex
    if record['kind'] == 'raster':
        targets = soup.find_all('img', attrs={'data-asset-id': record['asset_id']})
    elif record['kind'] == 'row_separator':
        targets = [tag for tag in soup.find_all('span', attrs={'data-inline-latex': True})
                   if str(tag['data-inline-latex']).startswith(r'\begin{cases}')]
    else:
        targets = [tag for tag in soup.find_all('span') if '{' in _plain(tag)
                   and not tag.find('span') and 'Решите систему неравенств' in _plain(tag)]
        if len(targets) == 1:
            prompt = BeautifulSoup('<p>Решите систему неравенств</p>', 'html.parser').p
            targets[0].insert_before(prompt)
    if len(targets) != 1:
        raise ValueError('reviewed system node is missing or ambiguous')
    targets[0].replace_with(replacement)


def _repair_options(soup: BeautifulSoup) -> bool:
    """Unify four choices in one table with shared equal-width columns."""
    tables = soup.find_all('table')
    if tables:
        cells = [cell for table in tables for cell in table.find_all('td')]
        labels = [_plain(cell) for cell in cells]
        if len(cells) != 4 or any(not re.match(rf'^{i}\)', text) for i, text in enumerate(labels, 1)):
            return False
        containers = tables
        contents = [cell.decode_contents() for cell in cells]
    else:
        lists = soup.find_all('ol', attrs={'data-layout': 'source-options'})
        if len(lists) != 1:
            return False
        items = lists[0].find_all('li', recursive=False)
        if len(items) != 4:
            raise ValueError('source options list must have exactly four entries')
        containers = lists
        contents = [f'{i}) {item.decode_contents()}' for i, item in enumerate(items, 1)]
    markup = ('<table data-layout="media-grid"><colgroup><col width="260"/><col width="260"/></colgroup><tbody>'
              + ''.join('<tr>' + ''.join(f'<td>{content}</td>' for content in contents[start:start+2])
                        + '</tr>' for start in (0, 2)) + '</tbody></table>')
    fragment = BeautifulSoup(markup, 'html.parser')
    if len(containers) == 1 and str(containers[0]) == str(fragment.table):
        return False
    for table in list(fragment.contents):
        containers[0].insert_before(table)
    for container in containers:
        container.decompose()
    return True


def _center_system(soup: BeautifulSoup, case: Any) -> bool:
    """Place the formula in a centered block while retaining surrounding prose."""
    if case.find_parent('center') is not None:
        return False
    center = soup.new_tag('center')
    paragraph = soup.new_tag('p')
    center.append(paragraph)
    parent = case.find_parent('p')
    if parent is None:
        anchor = case
        while getattr(anchor.parent, 'name', None) in ('span', 'i', 'b', 'em', 'strong'):
            anchor = anchor.parent
        anchor.insert_before(center)
        paragraph.append(case.extract())
        if anchor is not case and not anchor.get_text(strip=True) and not anchor.find(['img', 'span'], attrs={'data-inline-latex': True}):
            anchor.decompose()
    else:
        parent.insert_after(center)
        paragraph.append(case.extract())
        if not parent.get_text(strip=True).strip(' .') and not parent.find('img'):
            parent.decompose()
    return True


def _remove_empty_option_labels(soup: BeautifulSoup) -> bool:
    """Remove empty or number-only leftovers beside four complete table choices."""
    cells = soup.find_all('td')
    if len(cells) != 4 or any(not re.match(rf'^{i}\)', _plain(cell)) for i, cell in enumerate(cells, 1)):
        return False
    changed = False
    for options in soup.find_all('ol', attrs={'data-layout': 'source-options'}):
        items = options.find_all('li', recursive=False)
        number_only = (len(items) == 4 and
                       [_plain(item) for item in items] == ['1', '2', '3', '4'] and
                       not options.find('img') and
                       not options.find(attrs={'data-inline-latex': True}))
        if number_only or (not options.get_text(strip=True) and not options.find(['img', 'span'])):
            options.decompose()
            changed = True
    for paragraph in soup.find_all('p'):
        if paragraph.find_parent('td') is None and re.fullmatch(r'[1-4]\)', paragraph.get_text(strip=True)):
            paragraph.decompose()
            changed = True
    return changed


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Plan bounded presentation repairs; stop on missing formulas or source drift."""
    content = _normalized_content(context)
    condition = _section(content, 'condition')
    answer = _section(content, 'answer')
    if condition is None:
        raise ValueError('condition is required')
    answer_text = _plain(BeautifulSoup(str(answer['html']), 'html.parser')) if answer else ''
    raw = str(condition['html'])
    soup = BeautifulSoup(raw, 'html.parser')
    record = _EVIDENCE.get(str(context.get('problem_id')))
    changed = False
    if record:
        digest = condition_fingerprint(raw)
        if digest not in {record['condition_sha256'], record.get('repaired_condition_sha256'), record.get('replayed_condition_sha256'), *record.get('reviewed_condition_sha256s', [])}:
            raise ValueError('condition changed since equation review; review current source first')
        before = str(soup)
        _repair_system(soup, record)
        changed = before != str(soup)
    cases = [tag for tag in soup.find_all('span', attrs={'data-inline-latex': True})
             if str(tag['data-inline-latex']).startswith(r'\begin{cases}')]
    if len(cases) != 1 or r'\\' not in str(cases[0]['data-inline-latex']):
        raise ValueError('one verified multi-row LaTeX system is required')
    changed = _center_system(soup, cases[0]) or changed
    changed = _repair_options(soup) or changed
    changed = _remove_empty_option_labels(soup) or changed
    choice_count = len(soup.find_all('td'))
    warnings = (() if answer_text else ('source answer is missing; presentation repair preserves that state',))
    if choice_count == 4 and answer_text and answer_text not in {'1', '2', '3', '4'}:
        warnings = ('source answer is not a choice number; review answer separately',)
    obsolete = None
    if record and record['kind'] == 'raster' and any(a.get('asset_id') == record['asset_id'] for a in content.get('assets', [])):
        obsolete = {'transformation_target_id': 'asset:' + record['obsolete_asset_key'], 'operation': 'remove'}
    if not changed:
        return RepairPlan(answer_text, (obsolete,) if obsolete else (), warnings)
    keys = tuple(dict.fromkeys(str(img['data-asset-key'])
                              for img in soup.find_all('img', attrs={'data-asset-key': True})))
    return RepairPlan(answer_text, (_section_transformation(
        condition, 'condition', str(condition.get('title') or 'Условие'), str(soup), asset_keys=keys,
    ),) + ((obsolete,) if obsolete else ()), warnings)
