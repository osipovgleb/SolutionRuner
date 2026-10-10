"""Verify reviewed formula restoration, option order, drift guards and idempotency."""
from copy import deepcopy
import json
from pathlib import Path

from bs4 import BeautifulSoup
import pytest

from solution_runner.pipelines.core.content_runtime import _apply_record, _prepared_record
from solution_runner.pipelines.equations.inequality_systems import build_context_repair_plan

FIXTURES = json.loads((Path(__file__).parent / 'fixtures/inequality_systems.json').read_text())
RULE = 'inequality-systems-reviewed-presentation'


def _condition(context):
    """Return the fixture's exact condition section."""
    return next(s for s in context['normalized_content']['sections'] if s['key'] == 'condition')


def _apply(context, transformations):
    """Model condition rewrites without modifying answers, solutions or source sections."""
    result = deepcopy(context)
    for change in transformations:
        if change['operation'] == 'remove':
            result['normalized_content']['assets'] = [a for a in result['normalized_content']['assets'] if 'asset:' + a['asset_key'] != change['transformation_target_id']]
        else:
            _condition(result).update(change['value'])
    return result


@pytest.mark.parametrize('sid', ['322334', '322344', '404296'])
def test_controls_restore_formula_preserve_options_and_converge(sid):
    context = deepcopy(FIXTURES[sid])
    before = BeautifulSoup(_condition(context)['html'], 'html.parser')
    plan = build_context_repair_plan(context)
    assert len(plan.transformations) == (2 if sid == '404296' else 1)
    after = BeautifulSoup(plan.transformations[0]['value']['html'], 'html.parser')
    formula = after.find('span', attrs={'data-inline-latex': True})['data-inline-latex']
    assert r'\\' in formula
    old_ids = [i['data-asset-id'] for i in before.find_all('img')]
    new_ids = [i['data-asset-id'] for i in after.find_all('img')]
    assert new_ids == (old_ids[1:] if sid == '404296' else old_ids)
    assert len(after.find_all('table', attrs={'data-layout': 'media-grid'})) == 1
    assert [len(row.find_all('td')) for row in after.table.find_all('tr')] == [2, 2]
    assert [col['width'] for col in after.table.find_all('col')] == ['260', '260']
    assert after.find('span', attrs={'data-inline-latex': True}).find_parent('center') is not None
    assert [cell.get_text(' ', strip=True).split(')')[0] for cell in after.find_all('td')] == ['1', '2', '3', '4']
    repaired = _apply(context, plan.transformations)
    assert build_context_repair_plan(repaired).transformations == ()
    assert [s for s in repaired['normalized_content']['sections'] if s['key'] != 'condition'] == [s for s in context['normalized_content']['sections'] if s['key'] != 'condition']


def test_reference_only_gets_the_shared_option_grid():
    """Keep the reference formula while replacing independently sized rows."""
    context = FIXTURES['311672']
    plan = build_context_repair_plan(context)
    after = _apply(context, plan.transformations)
    assert build_context_repair_plan(after).transformations == ()


def test_changed_reviewed_condition_is_blocked():
    context = deepcopy(FIXTURES['322344'])
    _condition(context)['html'] = _condition(context)['html'].replace('35', '36')
    with pytest.raises(ValueError, match='changed since equation review'):
        build_context_repair_plan(context)


def test_unknown_raster_is_blocked():
    context = deepcopy(FIXTURES['404296'])
    context['problem_id'] = 'unreviewed'
    with pytest.raises(ValueError, match='verified multi-row'):
        build_context_repair_plan(context)


def test_transient_mcp_annotations_do_not_change_review_fingerprint():
    context = deepcopy(FIXTURES['322344'])
    _condition(context)['html'] = _condition(context)['html'].replace('<img ', '<img data-transformation-target-id="asset:image_1" ')
    assert build_context_repair_plan(context).transformations


class Gateway:
    """Expose authoritative readback and count writes for shared-runtime tests."""

    def __init__(self, context, discard=False):
        """Freeze the initial problem and optionally simulate a lost write."""
        self.context = deepcopy(context)
        self.discard = discard
        self.writes = 0

    def get_problem_context(self, problem_id):
        """Return the current problem, including missing answer sections."""
        assert problem_id == self.context['problem_id']
        return deepcopy(self.context)

    def apply_problem_transformations(self, problem_id, transformations):
        """Apply only the condition rewrite unless simulating a broken backend."""
        self.writes += 1
        if not self.discard:
            self.context = _apply(self.context, transformations)


@pytest.mark.parametrize('discard', [False, True])
def test_shared_runtime_accepts_missing_answer_and_requires_readback(discard):
    context = deepcopy(FIXTURES['322334'])
    gateway = Gateway(context, discard)
    child = {'id': context['problem_id'], 'source_problem_id': '322334'}
    record = _prepared_record(gateway, child, None, RULE)
    assert record['status'] == 'prepared'
    assert record['expected_answer'] == ''
    result = _apply_record(gateway, record, None, RULE)
    assert result['status'] == ('failed' if discard else 'applied')
    assert gateway.writes == 1
    if not discard:
        assert _apply_record(gateway, record, None, RULE)['status'] == 'already_complete'
        assert gateway.writes == 1


def test_invalid_source_answer_is_reported_but_not_rewritten():
    """Expose 404296's invalid 0000 answer separately from presentation changes."""
    plan = build_context_repair_plan(FIXTURES['404296'])
    assert plan.answer == '0000'
    assert plan.warnings == ('source answer is not a choice number; review answer separately',)
    assert all(change['transformation_target_id'].startswith('section:condition') or change['operation'] == 'remove' for change in plan.transformations)

@pytest.mark.parametrize('sid', ['320003', '320006', '320007', '320009'])
def test_live_layout_controls_share_columns_and_center_formula(sid):
    """Keep every choice while fixing centered systems and mixed text/image grids."""
    fixtures = json.loads((Path(__file__).parent / 'fixtures/inequality_system_layout.json').read_text())
    context = fixtures[sid]
    before = BeautifulSoup(_condition(context)['html'], 'html.parser')
    plan = build_context_repair_plan(context)
    repaired = _apply(context, plan.transformations)
    after = BeautifulSoup(_condition(repaired)['html'], 'html.parser')
    assert after.find('span', attrs={'data-inline-latex': True}).find_parent('center')
    assert len(after.find_all('table')) == 1
    assert [col['width'] for col in after.table.find_all('col')] == ['260', '260']
    assert [cell.decode_contents() for cell in before.find_all('td')] == [cell.decode_contents() for cell in after.find_all('td')]
    assert build_context_repair_plan(repaired).transformations == ()

@pytest.mark.parametrize('sid', ['340832', '340858'])
def test_number_only_option_list_is_removed_without_changing_choices(sid):
    """Drop parser-produced 1/2/3/4 lists when the four actual choices are intact."""
    fixtures = json.loads((Path(__file__).parent / 'fixtures/inequality_system_number_only_options.json').read_text())
    context = fixtures[sid]
    before = BeautifulSoup(_condition(context)['html'], 'html.parser')
    repaired = _apply(context, build_context_repair_plan(context).transformations)
    after = BeautifulSoup(_condition(repaired)['html'], 'html.parser')
    assert not after.find('ol', attrs={'data-layout': 'source-options'})
    assert [cell.decode_contents() for cell in before.find_all('td')] == [cell.decode_contents() for cell in after.find_all('td')]
    assert build_context_repair_plan(repaired).transformations == ()


def test_real_option_list_is_preserved_beside_complete_table():
    """Never remove a list that contains substantive answer text."""
    context = deepcopy(json.loads((Path(__file__).parent / 'fixtures/inequality_system_number_only_options.json').read_text())['340858'])
    _condition(context)['html'] = _condition(context)['html'].replace('<li>4</li>', '<li>4 или 5</li>')
    plan = build_context_repair_plan(context)
    after = _apply(context, plan.transformations)
    assert '4 или 5' in _condition(after)['html']
