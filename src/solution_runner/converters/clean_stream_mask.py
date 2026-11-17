"""Detect removable alpha regions and restore pixels in raster images."""

import cv2
import numpy as np


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
    roi_source = "base"

    def _select_components(src_mask: np.ndarray, roi_m: np.ndarray):
        num, labels, stats, _ = cv2.connectedComponentsWithStats(
            src_mask, connectivity=8
        )
        selected_local = []
        keep_local = np.zeros((h, w), dtype=np.uint8)

        for i in range(1, num):
            x, y, ww, hh, area = stats[i]
            if area < min_area or area > max_area:
                continue
            component_mask = (labels == i).astype(np.uint8) * 255
            if cv2.countNonZero(cv2.bitwise_and(component_mask, roi_m)) > 0:
                selected_local.append((area, x, y, ww, hh))
                keep_local = cv2.bitwise_or(keep_local, component_mask)

        return selected_local, keep_local

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

    # считаем только кандидатов в зоне ROI
    roi_mask = np.zeros((h, w), dtype=np.uint8)
    roi_mask[y0:, x0:] = 255

    if use_anchor and anchor_bbox_norm is not None:
        ax0n, ay0n, ax1n, ay1n = anchor_bbox_norm
        ax0 = max(0, int(ax0n * w) - int(max(0, anchor_margin_x)))
        ay0 = max(0, int(ay0n * h) - int(max(0, anchor_margin_y)))
        ax1 = min(w, int(ax1n * w) + int(max(0, anchor_margin_x)) + 1)
        ay1 = min(h, int(ay1n * h) + int(max(0, anchor_margin_y)) + 1)
        if ax1 > ax0 and ay1 > ay0:
            anchor_mask = np.zeros((h, w), dtype=np.uint8)
            anchor_mask[ay0:ay1, ax0:ax1] = 255
            # гибридная стратегия: анкер + базовый ROI, чтобы не упускать смещения
            roi_mask = cv2.bitwise_or(roi_mask, anchor_mask)
            roi_source = "anchor+base"
        else:
            roi_source = "base"

    roi_candidates = cv2.bitwise_and(clean_mask, roi_mask)

    min_area = max(min_area_abs, int(h * w * min_area_ratio))
    max_area = int(h * w * max_area_ratio)

    selected, keep = _select_components(roi_candidates, roi_mask)

    fallback = "none"
    # fallback 1: use all non-opaque pixels inside ROI
    if not selected and roi_candidates.sum() > 0:
        fallback = "roi_all"
        keep = roi_candidates.copy()
        y, x = np.where(keep > 0)
        selected = [
            (
                len(x),
                int(x.min()),
                int(y.min()),
                int(x.max() - x.min() + 1),
                int(y.max() - y.min() + 1),
            )
        ]
    if keep.sum() == 0:
        # legacy behaviour: if no component matched, take all non-opaque pixels in ROI
        if roi_candidates.sum() > 0:
            fallback = "roi_all"
            keep = roi_candidates.copy()
            y, x = np.where(keep > 0)
            selected = [
                (
                    len(x),
                    int(x.min()),
                    int(y.min()),
                    int(x.max() - x.min() + 1),
                    int(y.max() - y.min() + 1),
                )
            ]
        else:
            # final fallback for legacy behavior: use all non-opaque pixels
            fallback = "global"
            keep = raw_mask.copy()
            y, x = np.where(keep > 0)
            selected = (
                [
                    (
                        len(x),
                        int(x.min()),
                        int(y.min()),
                        int(x.max() - x.min() + 1),
                        int(y.max() - y.min() + 1),
                    )
                ]
                if len(x)
                else []
            )
    elif strict_alpha and total_non_opaque > 0:
        selected_ratio = int(keep.sum() // 255) / float(total_non_opaque)
        if selected_ratio < strict_capture_ratio:
            # адаптивно расширяем ROI вверх только если не хватает прозрачных пикселей
            right_side = np.zeros((h, w), dtype=np.uint8)
            right_side[:, x0:] = 255
            right_mask = cv2.bitwise_and(clean_mask, right_side)
            right_y = np.where(right_mask > 0)[0]
            if len(right_y) > 0:
                alt_y0 = max(0, int(right_y.min()))
                if alt_y0 < y0:
                    alt_roi = np.zeros((h, w), dtype=np.uint8)
                    alt_roi[alt_y0:, x0:] = 255
                    alt_selected, alt_keep = _select_components(
                        cv2.bitwise_and(clean_mask, alt_roi), alt_roi
                    )
                    alt_pixels = int(alt_keep.sum() // 255)
                    if alt_pixels > int(keep.sum() // 255):
                        selected = alt_selected
                        keep = alt_keep
                        y0 = alt_y0
                        fallback = "roi_strict_relaxed"
                        if len(alt_selected) > 0:
                            selected = alt_selected

        # дополнительный строгий мостик: добрать ближайшие части знака, если ROI режет маркер
        selected_ratio = int(keep.sum() // 255) / float(max(1, total_non_opaque))
        if keep.sum() > 0 and (
            selected_ratio < strict_capture_ratio
            or (
                str(fallback).startswith("roi_strict_relaxed")
                and int(keep.sum() // 255) < total_non_opaque
            )
        ):
            strict_bridge = max(
                1, int(max(1, max(anchor_margin_x, anchor_margin_y) / 3))
            )
            dist = cv2.distanceTransform((keep == 0).astype(np.uint8), cv2.DIST_L2, 3)
            bridge = ((dist <= strict_bridge).astype(np.uint8) * 255) & raw_mask
            bridge_added = cv2.bitwise_and(bridge, cv2.bitwise_not(keep))
            if bridge_added.sum() > 0:
                keep = cv2.bitwise_or(keep, bridge)
                fallback = (
                    "strict_neighbor_bridge"
                    if fallback == "none"
                    else f"{fallback}+strict_neighbor_bridge"
                )

    strict_tail_added = 0
    strict_tail_gap = 0
    strict_tail_bbox = None
    if keep.sum() > 0 and total_non_opaque > 0:
        selected_ratio = int(keep.sum() // 255) / float(total_non_opaque)
        if strict_alpha:
            strict_tail_gap = 4 if selected_ratio >= 0.9 else 10
        else:
            strict_tail_gap = 10 if selected_ratio < 1.0 else 0

        if strict_tail_gap > 0:
            missing = cv2.bitwise_and(raw_mask, cv2.bitwise_not(keep))
            if missing.sum() > 0:
                ys_keep, xs_keep = np.where(keep > 0)
                x0_tail = max(0, int(xs_keep.min()) - 24)
                x1_tail = min(w, int(xs_keep.max()) + 25)
                y0_tail = max(0, int(ys_keep.min()) - 12)
                y1_tail = min(h, int(ys_keep.max()) + 13)
                dist = cv2.distanceTransform(
                    (keep == 0).astype(np.uint8), cv2.DIST_L2, 3
                )
                num, labels, stats, _ = cv2.connectedComponentsWithStats(
                    missing, connectivity=8
                )

                tail_mask = np.zeros((h, w), dtype=np.uint8)
                for i in range(1, num):
                    x, y, ww, hh, area = stats[i]
                    if area <= 0 or area > 200:
                        continue
                    if (
                        x + ww < x0_tail
                        or x >= x1_tail
                        or y + hh < y0_tail
                        or y >= y1_tail
                    ):
                        continue
                    comp_mask = (labels == i).astype(np.uint8) * 255
                    comp_min_dist = (
                        dist[comp_mask > 0].min() if np.any(comp_mask > 0) else np.inf
                    )
                    if float(comp_min_dist) <= float(strict_tail_gap):
                        tail_mask = cv2.bitwise_or(tail_mask, comp_mask)

                strict_tail_added = int(tail_mask.sum() // 255)
                if strict_tail_added > 0:
                    keep = cv2.bitwise_or(keep, tail_mask)
                    ys_added, xs_added = np.where(tail_mask > 0)
                    strict_tail_bbox = (
                        int(xs_added.min()),
                        int(ys_added.min()),
                        int(xs_added.max()),
                        int(ys_added.max()),
                    )
                    fallback = (
                        "strict_tail_fill"
                        if fallback == "none"
                        else f"{fallback}+strict_tail_fill"
                    )

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
        ys, xs = np.where(keep > 0)
        seed = rgba[ys, xs, :3].astype(np.float32)
        seed_color = seed.mean(axis=0)
        # ROI локально вокруг найденного watermark, чтобы не разрастаться куда не надо
        margin = max(0, int(color_expand_margin))
        lx0 = max(0, int(xs.min()) - margin)
        ly0 = max(0, int(ys.min()) - margin)
        lx1 = min(w, int(xs.max()) + margin + 1)
        ly1 = min(h, int(ys.max()) + margin + 1)
        local_roi = np.zeros((h, w), dtype=np.uint8)
        local_roi[ly0:ly1, lx0:lx1] = 255
        color_gate = np.sqrt(
            ((rgba[:, :, :3].astype(np.float32) - seed_color) ** 2).sum(axis=2)
        )
        color_gate = (
            (color_gate <= color_expand_tolerance) & (local_roi > 0) & (roi_mask > 0)
        ).astype(np.uint8) * 255

        # расти только по пикселям похожего цвета в локальном ROI
        filled = keep.copy()
        growth_kernel = np.ones((3, 3), np.uint8)
        for _ in range(int(color_expand_iters)):
            dil = cv2.dilate(filled, growth_kernel)
            add = cv2.bitwise_and(dil, color_gate)
            nxt = cv2.bitwise_or(filled, add)
            if int(nxt.sum()) == int(filled.sum()):
                break
            filled = nxt
        keep = filled

    if mask_dilate_iters > 0:
        sx = max(1, int(mask_dilate_x))
        sy = max(1, int(mask_dilate_y))
        dilate_kernel = np.ones((sy, sx), np.uint8)
        keep = cv2.dilate(keep, dilate_kernel, iterations=int(mask_dilate_iters))

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
