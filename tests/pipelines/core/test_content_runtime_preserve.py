"""Apply must compare the same editorial-solution policy used by dry-run."""
from copy import deepcopy
from dataclasses import replace

import pytest

from solution_runner.pipelines.core.content_runtime import (
    _content_rule_manifest,
    apply_frozen_manifest,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.models import ProblemTarget


class LocalGateway:
    """Keep all writes in memory and expose no Helpers or external API."""

    def __init__(self, *, solution=True, answer='220'):
        self.writes = []
        self.context = {
            'problem_id': 'local-problem',
            'source_problem_id': '137285',
            'normalized_content': {
                'format': 'teacherhelper-normalized', 'schema_version': 3,
                'assets': [], 'sections': [
                    {'key': 'condition', 'section_id': 'condition:1',
                     'html': '<p>Найдите значение выражения <span data-inline-latex="5\\sqrt{11}\\cdot2\\sqrt{2}\\cdot\\sqrt{22}"></span>.</p>'},
                    {'key': 'answer', 'section_id': 'answer:1', 'html': f'<p>{answer}</p>'},
                ],
            },
        }
        if solution:
            self.context['normalized_content']['sections'].append({
                'key': 'solution', 'section_id': 'solution:1',
                'html': '<p>Авторское решение, которое нужно сохранить.</p>',
            })

    def get_problem_context(self, problem_id):
        assert problem_id == 'local-problem'
        return deepcopy(self.context)

    def apply_problem_transformations(self, problem_id, transformations):
        assert problem_id == 'local-problem'
        self.writes.extend(deepcopy(transformations))
        sections = self.context['normalized_content']['sections']
        for change in transformations:
            key = change['transformation_target_id'].split(':')[1]
            sections[:] = [section for section in sections if section['key'] != key]
            sections.append(dict(change['value'], key=key, section_id=f'{key}:1'))
        return {}


def freeze(gateway, *, policy='preserve'):
    profile = replace(get_group_profile('137285'), existing_solution_policy=policy)
    target = ProblemTarget(problem_id='local-problem', source_problem_id='137285',
                           source_group_id=profile.source_group_id, group_key='137285', problem_order_index=0)
    return _content_rule_manifest(gateway, (target,), profile=profile,
                                 parent_asset_id=None, parent_solution_assets=(), max_workers=1)


def apply_locally(gateway, manifest, tmp_path):
    return apply_frozen_manifest(gateway, manifest, batch_size=1, max_workers=1,
                                 checkpoint_path=tmp_path / 'checkpoint.json')


@pytest.mark.parametrize('answer', ['220', '110'])
@pytest.mark.parametrize('readback', [False, True])
def test_apply_preserves_editorial_solution_and_can_repair_answer(tmp_path, answer, readback, monkeypatch):
    if readback:
        from solution_runner.pipelines.core import content_runtime
        original_handler = content_runtime._registered_handler
        monkeypatch.setattr(content_runtime, '_registered_handler',
                            lambda key: replace(original_handler(key), verify_content_readback=True))
    gateway = LocalGateway(answer=answer)
    original = deepcopy(gateway.context['normalized_content']['sections'][-1])
    manifest = freeze(gateway)
    assert manifest['records'][0]['preserve_existing_solution'] is True
    result = apply_locally(gateway, manifest, tmp_path)
    assert result['failed_count'] == 0
    assert result['already_complete_count' if answer == '220' else 'applied_count'] == 1
    assert next(section for section in gateway.context['normalized_content']['sections']
                if section['key'] == 'solution') == original
    assert all(change['value']['title'] == 'Ответ' for change in gateway.writes)
    assert apply_locally(gateway, manifest, tmp_path)['already_complete_count'] == 1


def test_preserve_adds_missing_solution(tmp_path):
    gateway = LocalGateway(solution=False)
    result = apply_locally(gateway, freeze(gateway), tmp_path)
    assert result['applied_count'] == 1
    assert [change['value']['title'] for change in gateway.writes] == ['Решение']


def test_rewrite_policy_still_replaces_editorial_solution(tmp_path):
    gateway = LocalGateway()
    result = apply_locally(gateway, freeze(gateway, policy='rewrite'), tmp_path)
    assert result['applied_count'] == 1
    assert [change['value']['title'] for change in gateway.writes] == ['Решение']


def test_preserve_policy_still_blocks_answer_drift_after_freezing(tmp_path):
    gateway = LocalGateway(answer='110')
    manifest = freeze(gateway)
    gateway.context['normalized_content']['sections'][0]['html'] = (
        '<p>Найдите значение выражения <span data-inline-latex="3\\sqrt{11}\\cdot2\\sqrt{2}\\cdot\\sqrt{22}"></span>.</p>'
    )
    result = apply_locally(gateway, manifest, tmp_path)
    assert result['failed_count'] == 1
    assert result['results'][0]['message'] == 'condition or computed answer drifted after prepare'
    assert gateway.writes == []
