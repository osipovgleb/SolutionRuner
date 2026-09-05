"""Prepare annulus condition assets with content-based type detection."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from html import unescape
import json
from pathlib import Path
import subprocess
import sys
import time
import re
from typing import Any, Callable, Literal, Protocol

from .geometry.ring import RingSvgGeometry, parse_ring_svg
from .models import GroupProfile, KnownCircleArea, PreparedGridRing, ProblemTarget
from .progress import ProgressReporter, TargetProgress


DEFAULT_RING_CONVERTER = (
    Path(__file__).resolve().parents[2]
    / "converters"
    / "png_to_svg_ring_by_contrast.py"
)


class RingAssetPreparationError(RuntimeError):
    """Report one target-local annulus preparation failure."""


@dataclass(frozen=True)
class ConditionAsset:
    """Carry one downloaded current condition asset and its declared metadata."""

    asset_id: str
    content_type: str
    alt_text: str
    data: bytes


class RingAssetGateway(Protocol):
    """Expose exact asset operations used by annulus preparation."""

    def download_original_condition_asset(self, target: ProblemTarget) -> ConditionAsset:
        """Download the original condition asset behind any prior replacement."""

    def get_problem_context(self, problem_id: str) -> dict[str, Any]:
        """Return normalized problem content used for task-local condition facts."""

    def upload_condition_svg(
        self,
        *,
        source_problem_id: str,
        svg_bytes: bytes,
        sha256: str,
    ) -> dict[str, str]:
        """Upload one verified condition SVG and return its identity."""

    def replace_condition_asset(
        self,
        target: ProblemTarget,
        *,
        replacement_asset_id: str,
        alt_text: str,
    ) -> dict[str, str]:
        """Replace image_1 and return authoritative target readback."""


RingConverter = Callable[[Path, Path], tuple[Path, dict[str, str]]]


def detect_known_circle_area(
    condition_html: str,
) -> tuple[KnownCircleArea, Fraction]:
    """Return the uniquely stated inner/outer circle area from one condition."""

    text = unescape(condition_html).replace("\u00ad", "")
    text = re.sub(r"<[^>]*>", " ", text)
    text = " ".join(text.lower().replace("\xa0", " ").split())
    matches = re.findall(
        r"(?:площадь\s+)?(внутреннего|внешнего)\s+круга\s+равна\s+"
        r"(\d+(?:[,.]\d+)?)",
        text,
    )
    if len(matches) != 1:
        raise RingAssetPreparationError("known circle area is missing or ambiguous")
    side_text, value_text = matches[0]
    value = Fraction(value_text.replace(",", "."))
    if value <= 0:
        raise RingAssetPreparationError("known circle area must be positive")
    return ("inner" if side_text == "внутреннего" else "outer"), value


def _condition_html(context: dict[str, Any]) -> str:
    """Return the single normalized condition section HTML."""

    content = context.get("normalized_content")
    sections = content.get("sections", []) if isinstance(content, dict) else []
    matches = [
        str(section.get("html") or "")
        for section in sections
        if isinstance(section, dict) and section.get("key") == "condition"
    ]
    if len(matches) != 1:
        raise RingAssetPreparationError("problem has no unique condition section")
    return matches[0]


def sniff_asset_kind(data: bytes, declared_content_type: str) -> Literal["svg", "raster"]:
    """Return the actual supported image kind from bytes, not stale metadata."""

    prefix = data.lstrip()[:256].lower()
    if prefix.startswith(b"<?xml") or prefix.startswith(b"<svg"):
        if b"<svg" in prefix or b"<svg" in data[:2048].lower():
            return "svg"
    if data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"BM"):
        return "raster"
    if data.startswith(b"\xff\xd8\xff"):
        return "raster"
    declared = declared_content_type.split(";", 1)[0].strip().lower()
    if declared == "image/svg+xml":
        raise ValueError("declared SVG content is not SVG")
    if declared.startswith("image/"):
        return "raster"
    raise ValueError("condition asset is neither SVG nor a supported raster image")


def _parse_converter_output(output: str) -> dict[str, str]:
    """Return stable key/value diagnostics emitted by the ring converter."""

    diagnostics: dict[str, str] = {}
    for raw_line in output.splitlines():
        key, separator, value = raw_line.partition("=")
        if separator and key.strip().replace("_", "").isalnum():
            diagnostics[key.strip()] = value.strip()
    return diagnostics


def run_ring_converter(
    source_path: Path,
    output_dir: Path,
    *,
    converter_path: Path = DEFAULT_RING_CONVERTER,
) -> tuple[Path, dict[str, str]]:
    """Run the existing deterministic raster-ring converter exactly once."""

    output_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        (
            sys.executable,
            str(converter_path),
            str(source_path),
            "--out-dir",
            str(output_dir),
            "--with-1cm",
        ),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = " ".join((completed.stderr or completed.stdout).split())[:2000]
        raise RingAssetPreparationError(
            f"ring converter failed with exit code {completed.returncode}: {message}"
        )
    diagnostics = _parse_converter_output(completed.stdout)
    candidates = sorted(output_dir.glob("*.svg"))
    if len(candidates) != 1:
        raise RingAssetPreparationError("ring converter did not produce one SVG")
    return candidates[0], diagnostics


def _raster_suffix(data: bytes, content_type: str) -> str:
    """Return a converter-readable suffix from the actual raster signature."""

    if data.startswith(b"BM"):
        return ".bmp"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    declared = content_type.split(";", 1)[0].lower()
    return ".bmp" if "bmp" in declared else ".png"


def _diagnostics(
    geometry: RingSvgGeometry,
    converter_diagnostics: dict[str, str],
) -> dict[str, object]:
    """Combine converter output with independently parsed SVG evidence."""

    for key, expected in (
        ("outer_radius_squared", geometry.outer_radius_squared),
        ("inner_radius_squared", geometry.inner_radius_squared),
    ):
        raw = converter_diagnostics.get(key)
        if raw is not None and int(raw) != expected:
            raise RingAssetPreparationError(
                f"converter {key} disagrees with SVG readback"
            )
    return {
        **converter_diagnostics,
        "svg_center": list(geometry.svg_center),
        "svg_outer_radius": geometry.svg_outer_radius,
        "svg_inner_radius": geometry.svg_inner_radius,
        "grid_cell_size": geometry.grid_cell_size,
    }


def _alt_text(geometry: RingSvgGeometry) -> str:
    """Return deterministic ring metadata for the current condition asset."""

    return (
        f"Кольцо: R₁²={geometry.outer_radius_squared}, "
        f"R₂²={geometry.inner_radius_squared}"
    )


def _report(
    reporter: ProgressReporter | None,
    profile: GroupProfile,
    target: ProblemTarget,
    progress: TargetProgress,
    action: str,
    *,
    severity: str = "success",
    details: dict[str, Any] | None = None,
) -> None:
    """Emit one compact target line when launcher reporting is available."""

    if reporter is not None:
        reporter.task(
            profile.theme_title,
            profile.group_key,
            target.source_problem_id,
            progress,
            action,
            severity=severity,
            stage="image",
            details=details,
        )


def prepare_ring_assets(
    gateway: RingAssetGateway,
    *,
    profile: GroupProfile,
    run_dir: Path,
    expected_targets: tuple[ProblemTarget, ...],
    apply: bool,
    batch_size: int = 10,
    batch_pause_seconds: float = 0.0,
    max_workers: int = 1,
    reporter: ProgressReporter | None = None,
    converter: RingConverter = run_ring_converter,
) -> tuple[PreparedGridRing, ...]:
    """Prepare every ring once, isolating failures and verifying each replacement."""

    if profile.geometry_kind != "ring":
        raise RingAssetPreparationError("ring preparation requires a ring profile")
    if batch_size <= 0 or batch_pause_seconds < 0:
        raise RingAssetPreparationError("invalid ring preparation batching")
    if not 1 <= max_workers <= 10:
        raise RingAssetPreparationError("max_workers must be between 1 and 10")
    run_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = run_dir / "inputs"
    artifacts_dir = run_dir / "artifacts"
    inputs_dir.mkdir(exist_ok=True)
    artifacts_dir.mkdir(exist_ok=True)
    prepared: list[PreparedGridRing] = []
    errors: list[dict[str, str]] = []
    total = len(expected_targets)
    for index, target in enumerate(expected_targets, start=1):
        progress = TargetProgress(index=index, total=total)
        try:
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
                condition_asset_id = replacement_asset_id
                _report(reporter, profile, target, progress, "TRANSFORMATION APPLIED")
            digest = hashlib.sha256(svg_bytes).hexdigest()
            prepared.append(
                PreparedGridRing(
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
            )
        except Exception as exc:  # noqa: BLE001 - isolate one source problem.
            message = " ".join(str(exc).split())[:2000]
            errors.append(
                {
                    "problem_id": target.problem_id,
                    "source_problem_id": target.source_problem_id,
                    "error": message,
                }
            )
            _report(
                reporter,
                profile,
                target,
                progress,
                "IMAGE FAILED",
                severity="error",
                details={"exception_type": type(exc).__name__, "exception": message},
            )
        if (
            apply
            and batch_pause_seconds
            and index < total
            and index % batch_size == 0
        ):
            time.sleep(batch_pause_seconds)
    (run_dir / "image-errors.json").write_text(
        json.dumps(errors, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return tuple(prepared)
