"""Detect removable alpha regions and restore pixels in raster images."""

from functools import partial

import cv2
import numpy as np

if __package__:
    from .clean_stream_mask_refine import (
        _expand_color,
        _fill_tail,
        _initial_selection,
        _region_mask,
        _relax_strict,
        _select_components,
    )
else:
    from clean_stream_mask_refine import (
        _expand_color,
        _fill_tail,
        _initial_selection,
        _region_mask,
        _relax_strict,
        _select_components,
    )


def _refine_mask(keep, pixel_data, growth, dilation, fallback):
    rgba, raw_mask, roi_mask = pixel_data
    grow_missing_px, color_expand_tolerance, color_expand_iters, color_expand_margin = (
        growth
    )
    mask_dilate_iters, mask_dilate_x, mask_dilate_y = dilation
    if keep.sum() > 0 and grow_missing_px > 0:
        # подхватить мелкие потерянные пиксели рядом с выбранной маской (обычно единичные точки)
        dist = cv2.distanceTransform((keep == 0).astype(np.uint8), cv2.DIST_L2, 3)
        bridge = ((dist <= grow_missing_px).astype(np.uint8) * 255) & raw_mask
        keep = cv2.bitwise_or(keep, cv2.bitwise_and(bridge, roi_mask))

    if (
        keep.sum() > 0
        and color_expand_tolerance > 0
        and color_expand_iters > 0
        and fallback != "global"
    ):
        keep = _expand_color(
            keep,
            rgba,
            roi_mask,
            color_expand_tolerance,
            color_expand_iters,
            color_expand_margin,
        )

    if mask_dilate_iters > 0:
        sx = max(1, int(mask_dilate_x))
        sy = max(1, int(mask_dilate_y))
        dilate_kernel = np.ones((sy, sx), np.uint8)
        keep = cv2.dilate(keep, dilate_kernel, iterations=int(mask_dilate_iters))

    return keep


def _mask_report(keep, selected, region, details):
    x0, y0, y0_init, w, h, roi_source, anchor_bbox_norm = region
    (
        fallback,
        total_non_opaque,
        strict_alpha,
        strict_capture_ratio,
        strict_tail_added,
        strict_tail_gap,
        strict_tail_bbox,
    ) = details
    ys, xs = np.where(keep > 0)
    bbox = (
        (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
        if len(xs)
        else None
    )

    return keep, {
        "selected": selected,
        "selected_mask_pixels": int(keep.sum() // 255),
        "fallback": fallback,
        "bbox": bbox,
        "selected_count": len(selected),
        "roi_bbox": (x0, y0, w - 1, h - 1),
        "x0": x0,
        "y0": y0,
        "y0_init": y0_init,
        "selected_ratio": int(keep.sum() // 255) / float(max(1, total_non_opaque)),
        "total_non_opaque": total_non_opaque,
        "size": (w, h),
        "strict_alpha": strict_alpha,
        "strict_capture_ratio": strict_capture_ratio,
        "strict_tail_added": strict_tail_added,
        "strict_tail_gap": strict_tail_gap,
        "strict_tail_bbox": strict_tail_bbox,
        "roi_source": roi_source,
        "anchor_bbox_norm": tuple(anchor_bbox_norm)
        if anchor_bbox_norm is not None
        else None,
    }


def alpha_mask_from_right_bottom(
    rgba: np.ndarray,
    right_ratio: float = 0.82,
    bottom_ratio: float = 0.88,
    alpha_threshold: int = 250,
    min_area_ratio: float = 0.00001,
    max_area_ratio: float = 0.30,
    min_area_abs: int = 1,
    grow_missing_px: float = 0.0,
    use_open_mask: bool = False,
    color_expand_tolerance: float = 0.0,
    color_expand_iters: int = 0,
    color_expand_margin: int = 8,
    mask_dilate_iters: int = 1,
    mask_dilate_x: int = 1,
    mask_dilate_y: int = 1,
    roi_x_extend: int = 0,
    roi_y_extend: int = 0,
    strict_alpha: bool = False,
    strict_capture_ratio: float = 0.85,
    use_anchor: bool = False,
    anchor_bbox_norm=None,
    anchor_margin_x: int = 24,
    anchor_margin_y: int = 12,
):
    h, w = rgba.shape[:2]
    alpha = rgba[:, :, 3]

    # пиксели с прозрачностью ниже порога: это и есть "маркер" водяного знака
    raw_mask = (alpha < alpha_threshold).astype(np.uint8) * 255
    if alpha_threshold <= 0:
        raw_mask[:] = 0
    total_non_opaque = int(raw_mask.sum() // 255)

    kernel = np.ones((3, 3), np.uint8)
    clean_mask = (
        cv2.morphologyEx(raw_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        if use_open_mask
        else raw_mask
    )

    # ROI in right-bottom: watermark usually sits there in this stream
    x0 = max(0, int(w * right_ratio) - max(0, int(roi_x_extend)))
    y0 = max(0, int(h * bottom_ratio) - max(0, int(roi_y_extend)))
    y0_init = y0

    _y_indices, x_indices = np.where(raw_mask > 0)
    if len(x_indices) == 0:
        return np.zeros((h, w), dtype=np.uint8), {
            "selected": [],
            "selected_mask_pixels": 0,
            "fallback": "none",
            "bbox": None,
            "x0": x0,
            "y0": y0,
            "total_non_opaque": total_non_opaque,
            "size": (w, h),
        }

    roi_mask, roi_source = _region_mask(
        (h, w),
        (x0, y0),
        anchor_bbox_norm if use_anchor else None,
        (anchor_margin_x, anchor_margin_y),
    )

    roi_candidates = cv2.bitwise_and(clean_mask, roi_mask)

    min_area = max(min_area_abs, int(h * w * min_area_ratio))
    max_area = int(h * w * max_area_ratio)

    select_components = partial(
        _select_components, min_area=min_area, max_area=max_area
    )

    selected, keep, fallback, should_relax = _initial_selection(
        roi_candidates, roi_mask, raw_mask, select_components
    )
    if should_relax and strict_alpha and total_non_opaque > 0:
        keep, selected, y0, fallback = _relax_strict(
            keep,
            selected,
            raw_mask,
            clean_mask,
            (
                x0,
                y0,
                strict_capture_ratio,
                total_non_opaque,
                anchor_margin_x,
                anchor_margin_y,
                fallback,
            ),
            select_components,
        )

    keep, fallback, strict_tail_added, strict_tail_gap, strict_tail_bbox = _fill_tail(
        keep, raw_mask, total_non_opaque, strict_alpha, fallback
    )

    keep = _refine_mask(
        keep,
        (rgba, raw_mask, roi_mask),
        (
            grow_missing_px,
            color_expand_tolerance,
            color_expand_iters,
            color_expand_margin,
        ),
        (mask_dilate_iters, mask_dilate_x, mask_dilate_y),
        fallback,
    )

    return _mask_report(
        keep,
        selected,
        (x0, y0, y0_init, w, h, roi_source, anchor_bbox_norm),
        (
            fallback,
            total_non_opaque,
            strict_alpha,
            strict_capture_ratio,
            strict_tail_added,
            strict_tail_gap,
            strict_tail_bbox,
        ),
    )


def apply_inpaint_alpha(
    rgba: np.ndarray,
    mask: np.ndarray,
    radius: int = 7,
    method: str = "telea_ns",
) -> np.ndarray:
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]

    if mask.sum() == 0:
        return rgba.copy()

    radius = max(1, int(radius))

    methods = {
        "telea": (cv2.INPAINT_TELEA,),
        "ns": (cv2.INPAINT_NS,),
        "telea_ns": (cv2.INPAINT_TELEA, cv2.INPAINT_NS),
        "ns_telea": (cv2.INPAINT_NS, cv2.INPAINT_TELEA),
        "telea_only": (cv2.INPAINT_TELEA,),
    }
    if not isinstance(method, str) or method not in methods:
        raise ValueError(f"unknown inpaint method: {method}")
    repaired = rgb
    for algorithm in methods[method]:
        repaired = cv2.inpaint(repaired, mask, radius, algorithm)

    out = rgba.copy()
    out[:, :, :3] = repaired
    out[:, :, 3] = np.where(mask > 0, 255, alpha)
    return out
