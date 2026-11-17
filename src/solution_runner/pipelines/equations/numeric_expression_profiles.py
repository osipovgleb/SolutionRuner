"""Assemble numeric-expression profiles in their original registry order."""

from solution_runner.pipelines.core.profile_definitions import _profile

from .numeric_log_profiles import TOPICS as _NUMERIC_LOG_PROFILES
from .numeric_power_profiles import TOPICS as _NUMERIC_POWER_PROFILES
from .numeric_radical_profiles import TOPICS as _NUMERIC_RADICAL_PROFILES
from .numeric_trig_expression_profiles import (
    TOPICS as _NUMERIC_TRIG_EXPRESSION_PROFILES,
)
from .numeric_trig_value_profiles import TOPICS as _NUMERIC_TRIG_VALUE_PROFILES

_TOPICS = (
    _NUMERIC_POWER_PROFILES
    + _NUMERIC_RADICAL_PROFILES
    + _NUMERIC_LOG_PROFILES
    + _NUMERIC_TRIG_VALUE_PROFILES
    + _NUMERIC_TRIG_EXPRESSION_PROFILES
)

_ROWS = sorted(
    (position, key, source_id, order, title, theme_order, theme_id, rule)
    for title, theme_order, theme_id, entries in _TOPICS
    for position, key, source_id, order, rule in entries
)

PROFILES = tuple(
    _profile(
        key,
        source_id,
        order,
        catalog_snapshot_id="41bc4d03-40cd-4407-8dea-df76e3f47ea8",
        category_key="8",
        theme_title=title,
        theme_order_index=theme_order,
        snapshot_theme_id=theme_id,
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=True,
    )
    for _position, key, source_id, order, title, theme_order, theme_id, rule in _ROWS
)
