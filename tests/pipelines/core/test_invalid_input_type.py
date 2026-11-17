"""Malformed inputs remain compatible with existing value-error handlers."""

from types import SimpleNamespace

import pytest

from solution_runner.pipelines.equations.quadratic_interval_choices import _polynomial
from solution_runner.pipelines.grid_polygon.solution_asset_repair import (
    _manifest_records,
)


def test_unsupported_polynomial_operator_is_a_compatible_type_error():
    with pytest.raises(ValueError, match="unsupported polynomial operator") as caught:
        _polynomial("1/x")
    assert isinstance(caught.value, TypeError)


def test_non_object_manifest_scope_is_a_compatible_type_error(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"scope": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="manifest scope is missing") as caught:
        _manifest_records(manifest, SimpleNamespace())
    assert isinstance(caught.value, TypeError)
