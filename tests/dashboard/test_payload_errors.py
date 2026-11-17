"""Malformed payloads keep the dashboard's existing validation contract."""

import pytest

from solution_runner.dashboard.attachments import save_images
from solution_runner.dashboard.previews import _card


def test_invalid_attachment_is_type_error_and_value_error(tmp_path):
    with pytest.raises(ValueError, match="Некорректное изображение") as caught:
        save_images(tmp_path, [None])
    assert isinstance(caught.value, TypeError)


def test_invalid_preview_content_is_type_error_and_value_error():
    with pytest.raises(ValueError, match="problem content is missing") as caught:
        _card({"problem_id": "id"}, None)
    assert isinstance(caught.value, TypeError)
