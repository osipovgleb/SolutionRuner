"""Prepare and verify one ring condition image."""

import hashlib
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from ..core.models import KnownCircleArea, PreparedGridRing
from .geometry.ring import parse_ring_svg


@dataclass(frozen=True)
class RingPreparationContext:
    gateway: Any
    profile: Any
    inputs_dir: Path
    artifacts_dir: Path
    converter: Any
    apply: bool
    reporter: Any


def _replace_ring(context, target, progress, svg_bytes, geometry):
    from .ring_asset_preparation import RingAssetPreparationError, _alt_text, _report

    gateway, reporter, profile = context.gateway, context.reporter, context.profile
    digest = hashlib.sha256(svg_bytes).hexdigest()
    uploaded = gateway.upload_condition_svg(
        source_problem_id=target.source_problem_id,
        svg_bytes=svg_bytes,
        sha256=digest,
    )
    replacement_asset_id = str(uploaded.get("source_asset_id") or "")
    if not replacement_asset_id:
        raise RingAssetPreparationError("condition upload has no asset identity")
    _report(reporter, profile, target, progress, "SVG UPLOADED")
    readback = gateway.replace_condition_asset(
        target,
        replacement_asset_id=replacement_asset_id,
        alt_text=_alt_text(geometry),
    )
    if str(readback.get("asset_id") or "") != replacement_asset_id:
        raise RingAssetPreparationError("condition replacement readback drifted")
    _report(reporter, profile, target, progress, "TRANSFORMATION APPLIED")
    return replacement_asset_id


def prepare_ring_target(context, target, progress):
    from .ring_asset_preparation import (
        _condition_html,
        _diagnostics,
        _raster_suffix,
        _report,
        detect_known_circle_area,
        sniff_asset_kind,
    )

    gateway, profile, inputs_dir, artifacts_dir, converter, apply, reporter = (
        context.gateway,
        context.profile,
        context.inputs_dir,
        context.artifacts_dir,
        context.converter,
        context.apply,
        context.reporter,
    )
    asset = gateway.download_original_condition_asset(target)
    _report(reporter, profile, target, progress, "DOWNLOADED", severity="info")
    kind = sniff_asset_kind(asset.data, asset.content_type)
    converter_diagnostics: dict[str, str] = {}
    replaced = False
    if kind == "svg":
        svg_path = artifacts_dir / f"{target.source_problem_id}.svg"
        svg_path.write_bytes(asset.data)
        condition_asset_id = asset.asset_id
    else:
        source_path = inputs_dir / (
            target.source_problem_id + _raster_suffix(asset.data, asset.content_type)
        )
        source_path.write_bytes(asset.data)
        target_output_dir = artifacts_dir / target.source_problem_id
        svg_path, converter_diagnostics = converter(
            source_path,
            target_output_dir,
        )
        _report(reporter, profile, target, progress, "CONVERTED", severity="info")
        condition_asset_id = f"preview-{target.problem_id}"
        replaced = True
    svg_bytes = svg_path.read_bytes()
    geometry = parse_ring_svg(svg_bytes)
    diagnostics = _diagnostics(geometry, converter_diagnostics)
    known_circle_area: KnownCircleArea | None = None
    given_circle_area: Fraction | None = None
    if profile.strategy_key == "annulus-from-known-area":
        known_circle_area, given_circle_area = detect_known_circle_area(
            _condition_html(gateway.get_problem_context(target.problem_id))
        )
    if apply and replaced:
        condition_asset_id = _replace_ring(
            context, target, progress, svg_bytes, geometry
        )
    digest = hashlib.sha256(svg_bytes).hexdigest()
    return PreparedGridRing(
        problem_id=target.problem_id,
        source_problem_id=target.source_problem_id,
        condition_asset_id=condition_asset_id,
        condition_svg_path=svg_path,
        condition_svg_sha256=digest,
        center=geometry.center,
        outer_point=geometry.outer_point,
        inner_point=geometry.inner_point,
        outer_radius_squared=geometry.outer_radius_squared,
        inner_radius_squared=geometry.inner_radius_squared,
        condition_was_replaced=replaced,
        converter_diagnostics=diagnostics,
        inner_center=geometry.inner_center,
        ring_alignment=geometry.alignment,
        known_circle_area=known_circle_area,
        given_circle_area=given_circle_area,
    )
