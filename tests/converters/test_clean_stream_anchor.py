"""Regression checks for tracking the watermark region between images."""

from types import SimpleNamespace

from solution_runner.converters.clean_stream_v5_from_links import _update_anchor


def test_anchor_tracks_bbox_and_resets_after_four_misses():
    args = SimpleNamespace(use_anchor=True, anchor_min_ratio=0.2)
    anchor, misses = _update_anchor(
        args,
        {"bbox": (10, 5, 30, 15), "size": (100, 50), "selected_ratio": 0.5},
        None,
        2,
    )
    assert anchor == (0.1, 0.1, 0.3, 0.3)
    assert misses == 0
    for _ in range(3):
        anchor, misses = _update_anchor(args, {}, anchor, misses)
        assert anchor == (0.1, 0.1, 0.3, 0.3)
    assert _update_anchor(args, {}, anchor, misses) == (None, 0)
