"""Refine selected alpha-mask regions using nearby pixels."""

import cv2
import numpy as np


def _fill_tail(keep, raw_mask, total_non_opaque, strict_alpha, fallback):
    h, w = raw_mask.shape
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

    return keep, fallback, strict_tail_added, strict_tail_gap, strict_tail_bbox


def _expand_color(
    keep,
    rgba,
    roi_mask,
    color_expand_tolerance,
    color_expand_iters,
    color_expand_margin,
):
    h, w = keep.shape
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

    return keep


def _relax_strict(keep, selected, raw_mask, clean_mask, settings, select_components):
    (
        x0,
        y0,
        strict_capture_ratio,
        total_non_opaque,
        anchor_margin_x,
        anchor_margin_y,
        fallback,
    ) = settings
    h, w = keep.shape
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
                alt_selected, alt_keep = select_components(
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
        strict_bridge = max(1, int(max(1, max(anchor_margin_x, anchor_margin_y) / 3)))
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

    return keep, selected, y0, fallback


def _initial_selection(roi_candidates, roi_mask, raw_mask, select_components):
    selected, keep = select_components(roi_candidates, roi_mask)

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
    should_relax = keep.sum() != 0
    if not should_relax:
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
    return selected, keep, fallback, should_relax


def _select_components(src_mask, roi_m, *, min_area, max_area):
    h, w = src_mask.shape
    num, labels, stats, _ = cv2.connectedComponentsWithStats(src_mask, connectivity=8)
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


def _region_mask(shape, origin, anchor_bbox_norm, margins):
    h, w = shape
    x0, y0 = origin
    anchor_margin_x, anchor_margin_y = margins
    roi_source = "base"
    # считаем только кандидатов в зоне ROI
    roi_mask = np.zeros((h, w), dtype=np.uint8)
    roi_mask[y0:, x0:] = 255

    if anchor_bbox_norm is not None:
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

    return roi_mask, roi_source
