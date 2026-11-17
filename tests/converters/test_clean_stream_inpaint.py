"""Inpainting methods retain their order and alpha behavior."""

import cv2
import numpy as np
import pytest

from solution_runner.converters.clean_stream_v5_from_links import apply_inpaint_alpha


@pytest.mark.parametrize(
    ("method", "algorithms"),
    [
        ("telea", (cv2.INPAINT_TELEA,)),
        ("telea_only", (cv2.INPAINT_TELEA,)),
        ("ns", (cv2.INPAINT_NS,)),
        ("telea_ns", (cv2.INPAINT_TELEA, cv2.INPAINT_NS)),
        ("ns_telea", (cv2.INPAINT_NS, cv2.INPAINT_TELEA)),
    ],
)
def test_inpaint_methods_match_explicit_opencv_sequence(method, algorithms):
    rng = np.random.default_rng(31)
    image = rng.integers(0, 256, (9, 9, 4), dtype=np.uint8)
    mask = np.zeros((9, 9), dtype=np.uint8)
    mask[3:6, 3:6] = 255
    expected_rgb = image[:, :, :3]
    for algorithm in algorithms:
        expected_rgb = cv2.inpaint(expected_rgb, mask, 2, algorithm)
    actual = apply_inpaint_alpha(image, mask, radius=2, method=method)
    np.testing.assert_array_equal(actual[:, :, :3], expected_rgb)
    np.testing.assert_array_equal(
        actual[:, :, 3], np.where(mask > 0, 255, image[:, :, 3])
    )


def test_empty_mask_is_copied_and_unknown_method_fails_for_nonempty_mask():
    image = np.zeros((5, 5, 4), dtype=np.uint8)
    mask = np.zeros((5, 5), dtype=np.uint8)
    assert apply_inpaint_alpha(image, mask, method="unknown") is not image
    mask[2, 2] = 255
    with pytest.raises(ValueError, match="unknown inpaint method"):
        apply_inpaint_alpha(image, mask, method="unknown")
