"""Assemble base-catalog profiles in their reviewed registry order."""

from solution_runner.pipelines.core.profile_definitions import _profile

from .base_algebra_profiles import TOPICS as _BASE_ALGEBRA_PROFILES
from .base_arithmetic_profiles import TOPICS as _BASE_ARITHMETIC_PROFILES
from .base_exponential_profiles import TOPICS as _BASE_EXPONENTIAL_PROFILES
from .base_irrational_profiles import TOPICS as _BASE_IRRATIONAL_PROFILES
from .base_logarithm_profiles import TOPICS as _BASE_LOGARITHM_PROFILES
from .base_other_profiles import TOPICS as _BASE_OTHER_PROFILES
from .base_polynomial_profiles import TOPICS as _BASE_POLYNOMIAL_PROFILES

_TOPICS = (
    _BASE_OTHER_PROFILES
    + _BASE_LOGARITHM_PROFILES
    + _BASE_EXPONENTIAL_PROFILES
    + _BASE_IRRATIONAL_PROFILES
    + _BASE_POLYNOMIAL_PROFILES
    + _BASE_ARITHMETIC_PROFILES
    + _BASE_ALGEBRA_PROFILES
)

_ROWS = sorted(
    (position, subposition, key, source_id, order, metadata, rule, rewrite)
    for metadata, rows in _TOPICS
    for position, subposition, key, source_id, order, rule, rewrite in rows
)

PROFILES = tuple(
    _profile(
        key,
        source_id,
        order,
        catalog_snapshot_id=catalog,
        category_key=category,
        theme_title=title,
        theme_order_index=theme_order,
        snapshot_theme_id=theme_id,
        expected_vertices=None,
        strategy_key=None,
        workflow_kind="content_rule",
        content_rule_key=rule,
        rewrite_existing_solution=rewrite,
    )
    for _position, _subposition, key, source_id, order, (
        catalog,
        category,
        title,
        theme_order,
        theme_id,
    ), rule, rewrite in _ROWS
)
