"""Command-line interfaces for polygon and ring conversion."""

import argparse
import sys
from pathlib import Path


def polygon_main(run):
    p = argparse.ArgumentParser(
        description="Deterministic PNG -> SVG from an alpha-channel grid"
    )
    p.add_argument("source", help="Path or URL to a raster image")
    p.add_argument("--out-dir", type=Path, default=Path("svg_from_contrast"))
    p.add_argument(
        "--pad-cells", type=int, default=2, help="Pad in cell units (2 by default)"
    )
    p.add_argument(
        "--cell-size",
        type=float,
        default=None,
        help="Cell size in pixels. If omitted and --template-svg is set, detect from template.",
    )
    p.add_argument(
        "--template-svg",
        type=Path,
        default=Path(__file__).resolve().with_name("template_from_lessons.svg"),
        help="SVG template used for cell size, grid style, fill, and outline.",
    )
    p.add_argument(
        "--auto-grid",
        action="store_true",
        help="Deprecated compatibility flag; the grid is always inferred from alpha.",
    )
    p.add_argument(
        "--no-template-grid",
        action="store_true",
        help="Do not copy <line> grid from template into result.",
    )
    p.add_argument(
        "--quantile", type=float, default=0.97, help="Contrast quantile from 0.0 to 1.0"
    )
    p.add_argument("--min-area", type=int, default=20, help="Minimum component area")
    p.add_argument("--close", type=int, default=1, help="Morphological close radius")
    p.add_argument(
        "--simplify",
        type=float,
        default=1.5,
        help="Unused for quad mode (kept for backward compatibility)",
    )
    args = p.parse_args()

    out = run(
        args.source,
        args.out_dir,
        args.pad_cells,
        args.quantile,
        args.min_area,
        args.close,
        args.simplify,
        not args.no_template_grid,
        args.cell_size,
        args.template_svg,
        args.auto_grid,
    )
    sys.stdout.write(f"{out}\n")


def ring_main(run):
    p = argparse.ArgumentParser(
        description="Deterministic raster ring -> SVG from integer grid points"
    )
    p.add_argument("source", help="Path or URL to a raster image")
    p.add_argument("--out-dir", type=Path, default=Path("svg_from_rings"))
    p.add_argument(
        "--pad-cells", type=int, default=1, help="Pad in cell units (1 by default)"
    )
    p.add_argument(
        "--cell-size",
        type=float,
        default=None,
        help="Cell size in pixels. If omitted and --template-svg is set, detect from template.",
    )
    p.add_argument(
        "--template-svg",
        type=Path,
        default=Path(__file__).resolve().with_name("template_from_lessons.svg"),
        help="SVG template used for cell size, grid style, fill, and outline.",
    )
    p.add_argument(
        "--with-1cm",
        "--with-scale-label",
        dest="auto_grid",
        action="store_true",
        help="Add a one-cell scale segment with the label '1 cm'.",
    )
    p.add_argument(
        "--no-template-grid",
        action="store_true",
        help="Do not copy <line> grid from template into result.",
    )
    p.add_argument(
        "--quantile", type=float, default=0.97, help="Contrast quantile from 0.0 to 1.0"
    )
    p.add_argument("--min-area", type=int, default=20, help="Minimum component area")
    p.add_argument("--close", type=int, default=1, help="Morphological close radius")
    p.add_argument(
        "--simplify",
        type=float,
        default=1.5,
        help="Unused for quad mode (kept for backward compatibility)",
    )
    args = p.parse_args()

    out = run(
        args.source,
        args.out_dir,
        args.pad_cells,
        args.quantile,
        args.min_area,
        args.close,
        args.simplify,
        not args.no_template_grid,
        args.cell_size,
        args.template_svg,
        args.auto_grid,
    )
    sys.stdout.write(f"{out}\n")
