"""Verify complete repair plans, independent answers and reusable SVG readback."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from solution_runner.pipelines.core.content_runtime import _prepared_record, _apply_record
from solution_runner.pipelines.equations.inequality_systems_complete import build_context_repair_plan

FIXTURES = json.loads((Path(__file__).parent / 'fixtures/inequality_systems.json').read_text())
RULE = 'inequality-systems-linear-complete'


class Gateway:
    """Model section/asset writes and canonical source-asset uploads."""

    def __init__(self, context):
        """Retain one current authoritative context and immutable uploaded assets."""
        self.context = deepcopy(context)
        self.assets = {}
        self.writes = 0
        self.uploads = 0

    def get_problem_context(self, problem_id):
        """Read a copy so a planner cannot alter the stored context."""
        return deepcopy(self.context)

    def get_problem_asset_target_context(self, problem_id, target_id):
        """Read the obsolete formula image before removing its transformation."""
        return {}

    def get_source_asset(self, asset_id):
        """Return immutable bytes metadata for reuse checks."""
        return {'source_asset': self.assets[asset_id]}

    def upload_solution_asset(self, *, source_problem_id, svg_bytes, sha256):
        """Return a checksum-addressed identity matching the real upload boundary."""
        assert hashlib.sha256(svg_bytes).hexdigest() == sha256
        asset_id = '00000000-0000-4000-8000-' + sha256[:12]
        self.assets[asset_id] = {'sha256': sha256, 'content_type': 'image/svg+xml'}
        self.uploads += 1
        return {'source_asset_id': asset_id, 'url': '/assets/' + asset_id, 'sha256': sha256}

    def apply_problem_transformations(self, problem_id, transformations):
        """Apply section and asset operations atomically for runtime convergence tests."""
        self.writes += 1
        content = self.context['normalized_content']
        for change in transformations:
            parts = change['transformation_target_id'].split(':')
            if parts[0] == 'section':
                section = next((s for s in content['sections'] if s['key'] == parts[1]), None)
                if section is None:
                    section = {'key': parts[1], 'section_id': parts[1] + ':1'}
                    content['sections'].append(section)
                section.update(deepcopy(change['value']))
            else:
                if change['operation'] == 'remove':
                    content['assets'] = [a for a in content['assets'] if a['asset_key'] != parts[1]]
                    continue
                asset = next((a for a in content['assets'] if a['asset_key'] == parts[1]), None)
                if asset is None:
                    asset = {'asset_key': parts[1]}
                    content['assets'].append(asset)
                asset.update(deepcopy(change['value']))


@pytest.mark.parametrize('sid,answer', [('311672','2'), ('322334','3'), ('322344','3'), ('404296','2'), ('311905','3')])
def test_runtime_completes_answers_solutions_diagrams_and_reuses_upload(sid, answer):
    """Freeze, apply and reread controls through shared runtime with no second write."""
    context = FIXTURES[sid]
    gateway = Gateway(context)
    child = {'problem_id': context['problem_id'], 'source_problem_id': sid}
    record = _prepared_record(gateway, child, None, RULE)
    assert record['status'] == 'prepared'
    assert record['expected_answer'] == answer
    assert len(record['generated_diagrams']) == 1
    assert _apply_record(gateway, record, None, RULE)['status'] == 'applied'
    assert gateway.uploads == gateway.writes == 1
    solution = BeautifulSoup(next(s['html'] for s in gateway.context['normalized_content']['sections'] if s['key'] == 'solution'), 'html.parser')
    centers = solution.find_all('center')
    assert centers[0].find('span', attrs={'data-inline-latex': True})
    assert centers[1].find('img', attrs={'data-asset-key': 'generated_inequality_intersection'})
    assert r'\in' in centers[2].find('span', attrs={'data-inline-latex': True})['data-inline-latex']
    assert solution.find_all('p')[-1].get_text(strip=True).endswith(f'{answer}.')
    if sid == '311905':
        assert 'source-options' not in next(s['html'] for s in gateway.context['normalized_content']['sections'] if s['key'] == 'condition')
    assert _apply_record(gateway, record, None, RULE)['status'] == 'already_complete'
    assert gateway.uploads == gateway.writes == 1


def test_changed_choices_are_blocked_even_if_old_answer_is_correct():
    """Do not infer a choice number from the current saved answer."""
    context = deepcopy(FIXTURES['311672'])
    section = next(s for s in context['normalized_content']['sections'] if s['key'] == 'condition')
    section['html'] = section['html'].replace('1)', '5)')
    with pytest.raises(ValueError, match='options changed'):
        build_context_repair_plan(context)


def test_updated_generated_diagram_remains_a_replayable_add():
    """A created diagram cannot become a rewrite of an absent source asset."""
    gateway = Gateway(FIXTURES['311672'])
    child = {'problem_id': gateway.context['problem_id'], 'source_problem_id': '311672'}
    record = _prepared_record(gateway, child, None, RULE)
    assert _apply_record(gateway, record, None, RULE)['status'] == 'applied'
    replacement = {'asset_key': 'generated_inequality_intersection',
                   'source_asset_id': 'replacement', 'url': '/assets/replacement'}
    plan = build_context_repair_plan(gateway.context, generated_solution_assets=(replacement,))
    asset = next(t for t in plan.transformations if t['transformation_target_id'].startswith('asset:'))
    assert asset['operation'] == 'add'


def test_reviewed_column_major_options_are_reordered_without_renumbering():
    """Preserve each labelled option when turning column-major order into rows."""
    gateway = Gateway(FIXTURES['355411'])
    child = {'problem_id': gateway.context['problem_id'], 'source_problem_id': '355411'}
    record = _prepared_record(gateway, child, None, RULE)
    assert record['status'] == 'prepared'
    assert _apply_record(gateway, record, None, RULE)['status'] == 'applied'
    assert _apply_record(gateway, record, None, RULE)['status'] == 'already_complete'

FORMULA_FIXTURES = json.loads((Path(__file__).parent / 'fixtures/inequality_formula_options.json').read_text())


@pytest.mark.parametrize('sid', sorted(FORMULA_FIXTURES))
def test_reviewed_formula_images_become_latex_and_converge(sid):
    """Preserve distractors and remove obsolete formula assets on all reviewed tasks."""
    context = FORMULA_FIXTURES[sid]
    gateway = Gateway(context)
    existing = next((a for a in context['normalized_content']['assets'] if a['asset_key'] == 'generated_inequality_intersection'), None)
    generated = ({'asset_key': existing['asset_key'], 'source_asset_id': existing['asset_id'], 'url': existing['url']},) if existing else ()
    plan = build_context_repair_plan(context, generated_solution_assets=generated)
    gateway.apply_problem_transformations(context['problem_id'], plan.transformations)
    condition = next(s['html'] for s in gateway.context['normalized_content']['sections'] if s['key'] == 'condition')
    soup = BeautifulSoup(condition, 'html.parser')
    assert len(soup.find_all('td')) == 4
    assert not soup.find('img')
    instruction = soup.find('em', string='В ответе укажите номер правильного варианта.')
    assert instruction is not None
    assert instruction.find_parent('p').find_next_sibling('table') == soup.table
    assert not any(a['asset_key'].startswith('image_') for a in gateway.context['normalized_content']['assets'])
    assert build_context_repair_plan(gateway.context, generated_solution_assets=generated).transformations == ()
    if sid == '404159':
        assert plan.answer == '2'
        assert r'6-3x>-18' in soup.find('span', attrs={'data-inline-latex': True})['data-inline-latex']
    if sid == '404241':
        assert '-2{,}7' in soup.find_all('td')[1].find('span', attrs={'data-inline-latex': True})['data-inline-latex']
