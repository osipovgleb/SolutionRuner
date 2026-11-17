"""Load and verify a locked polygon converter and its output identity."""

from __future__ import annotations

import importlib.util
import io
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if __package__:
    from .mcp_polygon_config import CONVERTER_PROFILE
    from .mcp_polygon_events import EventLogger
    from .mcp_polygon_models import CandidateRejected, PipelineError, PreparedAsset
    from .mcp_polygon_processing import _validate_write_batch_policy
    from .mcp_polygon_util import _sha256_file
else:
    from mcp_polygon_config import CONVERTER_PROFILE
    from mcp_polygon_events import EventLogger
    from mcp_polygon_models import CandidateRejected, PipelineError, PreparedAsset
    from mcp_polygon_processing import _validate_write_batch_policy
    from mcp_polygon_util import _sha256_file


def _load_converter(converter_path: Path) -> Any:
    """Load the exact converter file selected for this process."""

    module_name = "grid_png_converter_locked"
    if (
        __package__
        and converter_path.resolve().parent == Path(__file__).resolve().parent
    ):
        module_name = f"{__package__}.{module_name}"
    spec = importlib.util.spec_from_file_location(module_name, converter_path)
    if spec is None or spec.loader is None:
        raise PipelineError(f"cannot import converter: {converter_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "run", None)):
        raise PipelineError("converter module has no callable run function")
    return module


def _canonical_asset_key(output_sha256: str, converter_fingerprint: str) -> str:
    """Return a deterministic reusable source-asset key for exact SVG bytes."""

    return f"{CONVERTER_PROFILE}-{converter_fingerprint[:12]}-{output_sha256[:48]}"


def _polygon_alt_text(validation: dict[str, Any]) -> str:
    """Serialize validated lattice vertices as the exact image alt text."""

    vertices = validation.get("vertices")
    if not isinstance(vertices, list):
        raise CandidateRejected("validated polygon vertices are missing")
    return str([tuple(int(coordinate) for coordinate in point) for point in vertices])


def verify_first_deterministic_render(
    prepared: PreparedAsset,
    *,
    converter: Any,
    template_path: Path,
    run_dir: Path,
) -> None:
    """Render the first accepted input twice and require byte-identical artifacts."""

    check_dir = run_dir / "determinism-check"
    check_dir.mkdir(parents=True, exist_ok=True)
    check_svg = Path(
        converter.run(
            str(prepared.input_path),
            check_dir,
            2,
            0.97,
            20,
            1,
            1.5,
            True,
            None,
            template_path,
            False,
            expected_vertices=prepared.candidate.expected_vertices,
            output_stream=io.StringIO(),
        )
    )
    if check_svg.read_bytes() != prepared.svg_path.read_bytes():
        raise PipelineError("converter produced different SVG bytes for the same PNG")
    if (
        check_svg.with_suffix(".txt").read_bytes()
        != prepared.diagnostic_path.read_bytes()
    ):
        raise PipelineError("converter produced different diagnostics for the same PNG")


def prepare_run_inputs(
    args: Any, *, writes: bool
) -> tuple[str, Path, Path, str, str, Any]:
    """Validate write intent and lock the converter and template inputs."""
    if writes and args.confirm_catalog != args.catalog_snapshot_id:
        raise PipelineError(
            f"{args.mode} mode requires --confirm-catalog equal to "
            "--catalog-snapshot-id"
        )
    if writes:
        _validate_write_batch_policy(args)
    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        raise PipelineError(f"environment variable {args.api_key_env} is empty")
    converter_path = args.converter_path.resolve()
    template_path = args.template_path.resolve()
    if not converter_path.is_file() or not template_path.is_file():
        raise PipelineError("converter or SVG template file is missing")
    converter_fingerprint = _sha256_file(converter_path)
    template_fingerprint = _sha256_file(template_path)
    converter = _load_converter(converter_path)
    return (
        api_key,
        converter_path,
        template_path,
        converter_fingerprint,
        template_fingerprint,
        converter,
    )


@dataclass
class _DeterminismGate:
    """Verify exactly the first accepted render before any worker applies it."""

    converter: Any
    template_path: Path
    run_dir: Path
    logger: EventLogger | None = None
    verified: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def verify(self, prepared: PreparedAsset, logger: EventLogger) -> None:
        """Serialize the first repeat render and release later accepted assets."""

        with self.lock:
            if self.verified:
                return
            verify_first_deterministic_render(
                prepared,
                converter=self.converter,
                template_path=self.template_path,
                run_dir=self.run_dir,
            )
            self.verified = True
            logger.emit(
                "determinism_verified",
                source_problem_id=prepared.candidate.source_problem_id,
                asset_key=prepared.candidate.asset_key,
                output_sha256=prepared.output_sha256,
            )
