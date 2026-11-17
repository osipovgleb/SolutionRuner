"""Public model aliases retain their runtime inspection and isinstance behavior."""

from typing import get_args

from solution_runner.pipelines.core.models import (
    ContentRuleKey,
    PreparedFigure,
    PreparedGridPolygon,
    PreparedGridRing,
    WorkflowKind,
)


def test_profile_aliases_support_existing_runtime_introspection():
    assert get_args(WorkflowKind) == ("geometry", "content_rule")
    assert isinstance("rule", ContentRuleKey)


def test_prepared_figure_alias_remains_a_runtime_union():
    assert set(get_args(PreparedFigure)) == {PreparedGridPolygon, PreparedGridRing}
