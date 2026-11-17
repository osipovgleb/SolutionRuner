#!/usr/bin/env python3
import argparse
import io
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np
import requests
from PIL import Image

if __package__:
    from . import clean_stream_mask as _clean_stream_mask
else:
    import clean_stream_mask as _clean_stream_mask

alpha_mask_from_right_bottom = _clean_stream_mask.alpha_mask_from_right_bottom
apply_inpaint_alpha = _clean_stream_mask.apply_inpaint_alpha


def extract_id(url: str) -> str:
    try:
        query = parse_qs(urlparse(url).query)
    except (ValueError, TypeError, AttributeError):
        query = {}
    if query.get("id"):
        return query["id"][0]
    match = re.search(r"([0-9]{3,})", url)
    return match.group(1) if match else "unknown"


def read_image_from_url(url: str, timeout: int = 30):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()

    ctype = (r.headers.get("content-type") or "").lower()
    if "svg" in ctype or "xml" in ctype:
        raise ValueError(f"non-raster content: {ctype}")

    try:
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
    except (OSError, ValueError) as e:
        raise ValueError(f"cannot open image: {e}") from e

    return np.array(img)


def process_one(
    url: str,
    right_ratio: float = 0.82,
    bottom_ratio: float = 0.88,
    alpha_threshold: int = 250,
    min_area_abs: int = 1,
    grow_missing_px: float = 0.0,
    use_open_mask: bool = False,
    color_expand_tolerance: float = 0.0,
    color_expand_iters: int = 0,
    color_expand_margin: int = 8,
    mask_dilate_iters: int = 1,
    mask_dilate_x: int = 1,
    mask_dilate_y: int = 1,
    inpaint_radius: int = 7,
    inpaint_method: str = "telea_ns",
    roi_x_extend: int = 0,
    roi_y_extend: int = 0,
    strict_alpha: bool = False,
    strict_capture_ratio: float = 0.85,
    use_anchor: bool = False,
    anchor_bbox_norm=None,
    anchor_margin_x: int = 24,
    anchor_margin_y: int = 12,
):
    rgba = read_image_from_url(url)
    mask, info = alpha_mask_from_right_bottom(
        rgba,
        right_ratio=right_ratio,
        bottom_ratio=bottom_ratio,
        alpha_threshold=alpha_threshold,
        min_area_abs=min_area_abs,
        grow_missing_px=grow_missing_px,
        use_open_mask=use_open_mask,
        color_expand_tolerance=color_expand_tolerance,
        color_expand_iters=color_expand_iters,
        color_expand_margin=color_expand_margin,
        mask_dilate_iters=mask_dilate_iters,
        mask_dilate_x=mask_dilate_x,
        mask_dilate_y=mask_dilate_y,
        roi_x_extend=roi_x_extend,
        roi_y_extend=roi_y_extend,
        strict_alpha=strict_alpha,
        strict_capture_ratio=strict_capture_ratio,
        use_anchor=use_anchor,
        anchor_bbox_norm=anchor_bbox_norm,
        anchor_margin_x=anchor_margin_x,
        anchor_margin_y=anchor_margin_y,
    )

    if int(mask.sum() / 255) == 0:
        return rgba, mask, info

    out = apply_inpaint_alpha(rgba, mask, radius=inpaint_radius, method=inpaint_method)
    info["out_mask_pixels"] = int(mask.sum() // 255)
    return out, mask, info


def save_clean_path(out_dir: Path, url: str, idx: int) -> Path:
    fid = extract_id(url)
    return out_dir / f"{idx:04d}_{fid}_clean_inpaint_v5.png"


def main():
    parser = argparse.ArgumentParser(
        description="Batch clean via transparency-only v5 flow."
    )
    parser.add_argument(
        "source_file", type=Path, nargs="?", default=Path("source-image-links.txt")
    )
    parser.add_argument("--out-dir", type=Path, default=Path("v5_output"))
    parser.add_argument("--limit", type=int, default=217)
    parser.add_argument("--right-ratio", type=float, default=0.82)
    parser.add_argument("--bottom-ratio", type=float, default=0.88)
    parser.add_argument("--alpha-threshold", type=int, default=250)
    parser.add_argument("--grow-missing-px", type=float, default=0.0)
    parser.add_argument("--use-open-mask", action="store_true")
    parser.add_argument("--min-area-abs", type=int, default=1)
    parser.add_argument("--color-expand-tolerance", type=float, default=0.0)
    parser.add_argument("--color-expand-iters", type=int, default=0)
    parser.add_argument("--color-expand-margin", type=int, default=8)
    parser.add_argument(
        "--mask-dilate", type=int, default=1, help="mask dilation iterations"
    )
    parser.add_argument(
        "--mask-dilate-x", type=int, default=1, help="mask dilation kernel width"
    )
    parser.add_argument(
        "--mask-dilate-y", type=int, default=1, help="mask dilation kernel height"
    )
    parser.add_argument(
        "--roi-x-extend",
        type=int,
        default=0,
        help="extend ROI to the left by this many px",
    )
    parser.add_argument(
        "--roi-y-extend", type=int, default=0, help="extend ROI upward by this many px"
    )
    parser.add_argument(
        "--inpaint-radius", type=int, default=7, help="OpenCV inpaint radius"
    )
    parser.add_argument(
        "--inpaint-method",
        type=str,
        default="telea_ns",
        choices=["telea", "ns", "telea_ns", "ns_telea", "telea_only"],
        help="inpaint algorithm",
    )
    parser.add_argument("--max-output", type=int, default=0)
    parser.add_argument("--no-skip-errors", action="store_true")
    parser.add_argument(
        "--strict-alpha",
        action="store_true",
        help="inpaint only pixels from original alpha mask (no growth, no dilation, no color expansion)",
    )
    parser.add_argument(
        "--use-anchor",
        action="store_true",
        help="reuse previous frame bbox as ROI anchor",
    )
    parser.add_argument(
        "--anchor-margin-x", type=int, default=24, help="anchor ROI extend in x"
    )
    parser.add_argument(
        "--anchor-margin-y", type=int, default=12, help="anchor ROI extend in y"
    )
    parser.add_argument(
        "--anchor-min-ratio",
        type=float,
        default=0.20,
        help="save anchor when selected_ratio >= this",
    )
    parser.add_argument(
        "--strict-capture-ratio",
        type=float,
        default=0.85,
        help="minimal strict capture ratio before ROI relaxation",
    )

    args = parser.parse_args()

    if args.strict_alpha:
        args.color_expand_tolerance = 0.0
        args.color_expand_iters = 0
        args.color_expand_margin = 0
        args.mask_dilate = 0
        args.mask_dilate_x = 1
        args.mask_dilate_y = 1
        args.strict_capture_ratio = max(0.0, min(1.0, args.strict_capture_ratio))

    links = [
        l.strip()
        for l in args.source_file.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    if args.limit > 0:
        links = links[: args.limit]
    if args.max_output > 0:
        links = links[: args.max_output]

    args.out_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    skipped = 0
    anchor_bbox_norm = None
    anchor_miss = 0

    for idx, url in enumerate(links, start=1):
        try:
            out_arr, mask, info = process_one(
                url,
                right_ratio=args.right_ratio,
                bottom_ratio=args.bottom_ratio,
                alpha_threshold=args.alpha_threshold,
                grow_missing_px=args.grow_missing_px,
                use_open_mask=args.use_open_mask,
                min_area_abs=args.min_area_abs,
                color_expand_tolerance=args.color_expand_tolerance,
                color_expand_iters=args.color_expand_iters,
                color_expand_margin=args.color_expand_margin,
                mask_dilate_iters=args.mask_dilate,
                mask_dilate_x=args.mask_dilate_x,
                mask_dilate_y=args.mask_dilate_y,
                roi_x_extend=args.roi_x_extend,
                roi_y_extend=args.roi_y_extend,
                strict_alpha=args.strict_alpha,
                strict_capture_ratio=args.strict_capture_ratio,
                use_anchor=args.use_anchor,
                anchor_bbox_norm=anchor_bbox_norm,
                anchor_margin_x=args.anchor_margin_x,
                anchor_margin_y=args.anchor_margin_y,
                inpaint_radius=args.inpaint_radius,
                inpaint_method=args.inpaint_method,
            )
            mask_pixels = int(mask.sum() / 255)
            out_path = save_clean_path(args.out_dir, url, idx)
            if mask_pixels > 0:
                from PIL import Image

                Image.fromarray(out_arr, "RGBA").save(out_path)
            else:
                # no visible watermark by alpha; keep copy if needed
                from PIL import Image

                Image.fromarray(out_arr, "RGBA").save(out_path)

            ok += 1
            print(
                f"[OK] {idx:03d} {url} "
                f"| total_non_opaque={info['total_non_opaque']} "
                f"| mask={mask_pixels} (sel={info.get('selected_count')}) area={info['bbox']} "
                f"| ratio={info.get('selected_ratio'):.3f} "
                f"| anchor={info.get('anchor_bbox_norm')} "
                f"| roi_init={info.get('x0')},{info.get('y0_init')} -> {info.get('y0')} "
                f"| roi={info.get('roi_bbox')} roi_src={info.get('roi_source')} fallback={info['fallback']} "
                f"-> {out_path.name}"
            )

            selected_ratio = info.get("selected_ratio", 0.0) or 0.0
            if (
                args.use_anchor
                and info.get("bbox")
                and selected_ratio >= args.anchor_min_ratio
            ):
                w, h = info.get("size", (0, 0))
                if w > 0 and h > 0:
                    x0, y0, x1, y1 = info["bbox"]
                    anchor_bbox_norm = (
                        x0 / float(w),
                        y0 / float(h),
                        x1 / float(w),
                        y1 / float(h),
                    )
                    anchor_miss = 0
            elif args.use_anchor:
                anchor_miss += 1
                if anchor_miss >= 4:
                    anchor_bbox_norm = None
                    anchor_miss = 0
        except Exception as e:
            skipped += 1
            if args.no_skip_errors:
                continue
            print(f"[ERR] {idx:03d} {url} | {e}")

    print(f"Done. OK={ok} skipped={skipped} out-dir={args.out_dir}")


if __name__ == "__main__":
    main()
