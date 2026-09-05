"""Test deterministic selection and validation helpers for the MCP PNG runner."""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import threading
import unittest
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import cv2
import httpx
import numpy as np
from PIL import Image

from solution_runner.converters import mcp_grid_polygon_transformations as runner

from solution_runner.converters.mcp_grid_polygon_transformations import (
    AssetCandidate,
    CandidateRejected,
    CandidateStale,
    EventLogger,
    GroupScope,
    McpClient,
    PipelineError,
    PreparedAsset,
    RefreshedAsset,
    RollbackCandidate,
    ThemeScope,
    _canonical_asset_key,
    _execute_rollback,
    _polygon_alt_text,
    _problem_batches,
    _validate_write_batch_policy,
    _resume_inventory_from_run,
    _rollback_inventory_from_run,
    _unpack_mcp_result,
    _validate_png,
    _validate_diagnostics,
    apply_prepared_asset,
    build_group_inventory,
    discover_catalog_scope,
    prepare_candidate,
    refresh_candidate,
    verify_first_deterministic_render,
)
from solution_runner.converters.png_to_svg_by_contrast import (
    _fit_grid_axis,
    _promote_clean_grid_fundamental,
    _require_stable_grayscale_dilation_coordinates,
    _select_grid_for_quad,
    grayscale_shape_mask,
    quad_from_mask,
    run as run_contrast_converter,
)


class FakeMcpClient:
    """Return fixed MCP payloads for selection tests."""

    def __init__(self, responses: dict[str, list[dict]]) -> None:
        """Store queued responses by MCP tool name."""

        self.responses = responses
        self.calls = []

    def call(self, name: str, arguments=None, *, attempts: int = 3):
        """Pop the next fixed response for *name*."""

        del attempts
        self.calls.append((name, arguments))
        return self.responses[name].pop(0)


class RunnerHelpersTest(unittest.TestCase):
    """Cover the fail-closed pure helpers and group selection."""

    def test_bounded_map_uses_sliding_window_and_preserves_input_order(self) -> None:
        """Start task eleven when any initial worker frees without exceeding ten."""

        bounded_map = getattr(runner, "_bounded_map_ordered", None)
        self.assertIsNotNone(bounded_map)
        state_lock = threading.Lock()
        first_ten_started = threading.Barrier(10)
        release_slow_workers = threading.Event()
        eleventh_started = threading.Event()
        active = 0
        max_active = 0

        def work(value: int) -> int:
            """Hold nine initial workers until the eleventh task starts."""

            nonlocal active, max_active
            with state_lock:
                active += 1
                max_active = max(max_active, active)
            try:
                if value < 10:
                    first_ten_started.wait(timeout=2.0)
                    if value != 0:
                        self.assertTrue(release_slow_workers.wait(timeout=2.0))
                elif value == 10:
                    eleventh_started.set()
                    release_slow_workers.set()
                return value
            finally:
                with state_lock:
                    active -= 1

        results = bounded_map(tuple(range(12)), work, max_workers=10)

        self.assertTrue(eleventh_started.is_set())
        self.assertEqual(max_active, 10)
        self.assertEqual(results, tuple(range(12)))

    def test_alpha_grid_failure_falls_back_to_grayscale_grid(self) -> None:
        """A weak alpha lattice must not hide a valid grayscale lattice."""

        rgba = np.zeros((20, 20, 4), dtype=np.uint8)
        rgba[:, :, :3] = (80, 160, 220)
        rgba[2:18, 2:18, 3] = 255
        mask = np.zeros((20, 20), dtype=np.uint8)
        mask[2:18, 2:18] = 255
        polygon = [(2.0, 2.0), (17.0, 2.0), (17.0, 17.0), (2.0, 17.0)]
        grayscale_grid = {
            "source": "grayscale",
            "cell": 20.0,
            "x": {
                "observed": [2.0, 17.0],
                "origin": 2.0,
                "step": 20.0,
                "max_residual": 0.0,
                "coverage": 1.0,
            },
            "y": {
                "observed": [2.0, 17.0],
                "origin": 2.0,
                "step": 20.0,
                "max_residual": 0.0,
                "coverage": 1.0,
            },
        }
        prototype_info = {
            "bbox": (0.0, 0.0, 20.0, 20.0),
            "source_quad_before_snap": polygon,
            "source_quad_on_alpha_grid": polygon,
            "grid_indices": [(0, 0), (1, 0), (1, 1), (0, 1)],
            "source_grid_points": [(0, 0), (1, 0), (1, 1), (0, 1)],
            "grid_bounds": (-2, -2, 3, 3),
            "svg_size": (100.0, 100.0),
        }

        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch(
                "solution_runner.converters.png_to_svg_by_contrast.load_image",
                return_value=(rgba, "fixture.png"),
                ),
                patch(
                "solution_runner.converters.png_to_svg_by_contrast.alpha_shape_mask",
                return_value=(
                    mask,
                    {
                        "alpha_shape_threshold": 1,
                        "alpha_shape_bbox": (2, 2, 17, 17),
                    },
                ),
                ),
                patch(
                "solution_runner.converters.png_to_svg_by_contrast.infer_grid_from_alpha",
                side_effect=ValueError("square_grid_low_confidence"),
                ),
                patch(
                "solution_runner.converters.png_to_svg_by_contrast.infer_grid_from_grayscale",
                return_value=grayscale_grid,
                ) as grayscale_fallback,
                patch(
                "solution_runner.converters.png_to_svg_by_contrast.quad_from_mask",
                return_value=polygon,
                ),
                patch(
                "solution_runner.converters.png_to_svg_by_contrast._select_grid_for_quad",
                return_value=grayscale_grid,
                ),
                patch(
                "solution_runner.converters.png_to_svg_by_contrast.svg_for_mask",
                return_value=(polygon, prototype_info),
                ),
            ):
                try:
                    output = run_contrast_converter(
                        "fixture.png",
                        Path(temporary),
                        2,
                        0.97,
                        20,
                        1,
                        1.5,
                        True,
                        None,
                        None,
                        False,
                        expected_vertices=4,
                    )
                except ValueError as error:
                    self.fail(f"grayscale fallback was skipped: {error}")

        self.assertEqual(output.name, "fixture.svg")
        grayscale_fallback.assert_called_once_with(rgba)

    def test_triangle_dilation_consensus_uses_exactly_radii_zero_through_four(
        self,
    ) -> None:
        """Triangle acceptance must depend on all and only the audited radii."""

        mask = np.zeros((5, 5), dtype=np.uint8)
        polygon = [(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)]
        coordinates = [(1, 1), (5, 1), (1, 5)]
        with (
            patch(
                "solution_runner.converters.png_to_svg_by_contrast.quad_from_mask",
                return_value=polygon,
            ),
            patch(
                "solution_runner.converters.png_to_svg_by_contrast._snap_quad_to_alpha_grid",
                return_value=(polygon, coordinates),
            ),
            patch(
                "solution_runner.converters.png_to_svg_by_contrast._source_grid_coordinates",
                return_value=coordinates,
            ),
        ):
            result = _require_stable_grayscale_dilation_coordinates(
                mask,
                {},
                5,
                5,
                expected_vertices=3,
            )

        self.assertEqual(list(result), [0, 1, 2, 3, 4])

    def test_apply_batch_policy_allows_zero_pause(self) -> None:
        """The sequential MCP writer no longer requires an artificial delay."""

        _validate_write_batch_policy(
            SimpleNamespace(batch_size=10, batch_pause_seconds=0)
        )
        with self.assertRaisesRegex(PipelineError, "batches of 10"):
            _validate_write_batch_policy(
                SimpleNamespace(batch_size=9, batch_pause_seconds=0)
            )

    def _write_run_fixture(
        self,
        root: Path,
    ) -> tuple[Path, list[tuple[ThemeScope, list[GroupScope]]], list[AssetCandidate]]:
        """Write one valid four-target worklist and representative outcomes."""

        source_run = root / "source"
        source_run.mkdir()
        theme = ThemeScope("Трапеция", "theme-id", "284", 2, 1, 4)
        group = GroupScope("group-id", "27556", 0)
        candidates = [
            AssetCandidate(
                theme_title=theme.title,
                snapshot_theme_id=theme.snapshot_theme_id,
                theme_order_index=theme.order_index,
                source_group_id=group.source_group_id,
                group_key=group.group_key,
                group_order_index=group.order_index,
                problem_id=str(uuid4()),
                source_problem_id=str(100 + index),
                problem_order_index=index,
                asset_key="image_1",
                sections=("condition",),
                expected_vertices=4,
            )
            for index in range(4)
        ]
        targets = []
        for candidate in candidates:
            target = candidate.__dict__.copy()
            target["sections"] = list(candidate.sections)
            targets.append(target)
        basis = json.dumps(
            targets,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        worklist = {
            "schema_version": 1,
            "catalog_snapshot_id": "catalog",
            "source_site_id": "site",
            "category_key": "9",
            "theme_titles": [theme.title],
            "converter_sha256": "old-converter",
            "template_sha256": "template",
            "group_count": 1,
            "problem_count": 4,
            "target_count": 4,
            "worklist_sha256": hashlib.sha256(basis).hexdigest(),
            "targets": targets,
        }
        (source_run / "worklist.json").write_text(
            json.dumps(worklist, ensure_ascii=False), encoding="utf-8"
        )
        applied_source_asset_id = str(uuid4())
        events = [
            {
                "event": "run_start",
                "converter_sha256": "old-converter",
                "template_sha256": "template",
            },
            {
                "event": "asset_replaced",
                "theme": theme.title,
                "group_key": group.group_key,
                "problem_id": candidates[0].problem_id,
                "source_problem_id": candidates[0].source_problem_id,
                "asset_key": candidates[0].asset_key,
                "transformation_target_id": "asset:applied",
                "source_asset_id": applied_source_asset_id,
                "output_sha256": "a" * 64,
            },
            {
                "event": "asset_rejected",
                "theme": theme.title,
                "group_key": group.group_key,
                "problem_id": candidates[1].problem_id,
                "source_problem_id": candidates[1].source_problem_id,
                "asset_key": candidates[1].asset_key,
            },
            {
                "event": "asset_error",
                "theme": theme.title,
                "group_key": group.group_key,
                "source_problem_id": candidates[2].source_problem_id,
                "asset_key": candidates[2].asset_key,
                "stage": "prepare",
                "reason": (
                    "Client error '404 Not Found' for url "
                    "'https://example.test/problem-assets/id/content'"
                ),
            },
            {
                "event": "asset_error",
                "theme": theme.title,
                "group_key": group.group_key,
                "problem_id": candidates[3].problem_id,
                "source_problem_id": candidates[3].source_problem_id,
                "asset_key": candidates[3].asset_key,
                "stage": "apply",
                "reason": "502 Bad Gateway",
            },
        ]
        (source_run / "events.jsonl").write_text(
            "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
            encoding="utf-8",
        )
        return source_run, [(theme, [group])], candidates

    def test_unpack_mcp_text_json(self) -> None:
        """Text-only CallToolResult payloads remain supported."""

        result = {
            "content": [
                {"type": "text", "text": json.dumps({"answer": 42})},
            ]
        }
        self.assertEqual(_unpack_mcp_result(result), {"answer": 42})

    def test_png_metadata_accepts_valid_jpeg_bytes_as_raster(self) -> None:
        """A historical PNG MIME mismatch must not reject a decodable JPEG asset."""

        buffer = io.BytesIO()
        Image.new("RGB", (3, 2), color=(20, 40, 60)).save(buffer, format="JPEG")
        data = buffer.getvalue()

        try:
            digest, dimensions = _validate_png(
                data,
                {
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size_bytes": len(data),
                },
            )
        except CandidateRejected as exc:
            self.fail(f"valid JPEG raster was rejected: {exc}")

        self.assertEqual(digest, hashlib.sha256(data).hexdigest())
        self.assertEqual(dimensions, (3, 2))

    def test_bmp_metadata_accepts_valid_bmp_bytes_as_raster(self) -> None:
        """A BMP condition asset must reach the same deterministic converter."""

        buffer = io.BytesIO()
        Image.new("RGB", (3, 2), color=(20, 40, 60)).save(buffer, format="BMP")
        data = buffer.getvalue()

        digest, dimensions = _validate_png(
            data,
            {
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            },
        )

        self.assertEqual(digest, hashlib.sha256(data).hexdigest())
        self.assertEqual(dimensions, (3, 2))

    def test_colored_task_stage_log_contains_group_task_and_status(self) -> None:
        """Human logs show the requested colored per-task stage while JSON stays clean."""

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.jsonl"
            output = io.StringIO()
            with redirect_stdout(output):
                logger = EventLogger(path, color="always")
                logger.emit(
                    "source_downloaded",
                    theme="Трапеция",
                    group_key="27556",
                    source_problem_id="5217",
                    asset_key="image_1",
                )
                logger.close()
            console = output.getvalue()
            self.assertIn("Трапеция / group 27556", console)
            self.assertIn("Task 5217", console)
            self.assertIn("DOWNLOADED", console)
            self.assertIn("\033[", console)
            persisted = path.read_text(encoding="utf-8")
            self.assertNotIn("\033[", persisted)
            self.assertEqual(json.loads(persisted)["event"], "source_downloaded")

    def test_group_transition_and_target_count_are_red(self) -> None:
        """Each group announces its transition and current target count in red."""

        with tempfile.TemporaryDirectory() as temporary:
            output = io.StringIO()
            with redirect_stdout(output):
                logger = EventLogger(Path(temporary) / "events.jsonl", color="always")
                logger.emit(
                    "group_transition", theme="Трапеция", group_key="27556"
                )
                logger.emit(
                    "group_opened", theme="Трапеция", group_key="27556", tasks=52
                )
                logger.close()
            console = output.getvalue()
            self.assertIn("ПЕРЕХОЖУ К ГРУППЕ Трапеция / 27556", console)
            self.assertIn("ГРУППА ОТКРЫТА, ЦЕЛЕЙ 52", console)
            self.assertGreaterEqual(console.count("\033[31m"), 2)

    def test_polygon_alt_text_uses_exact_validated_vertex_list(self) -> None:
        """Persist the coordinate-list syntax requested for triangle and quad SVGs."""

        self.assertEqual(
            _polygon_alt_text({"vertices": [(8, 2), (1, 4), (1, 8), (8, 9)]}),
            "[(8, 2), (1, 4), (1, 8), (8, 9)]",
        )
        self.assertEqual(
            _polygon_alt_text({"vertices": [(8, 2), (1, 4), (1, 8)]}),
            "[(8, 2), (1, 4), (1, 8)]",
        )

    def test_resume_retries_old_renderer_and_transient_errors(self) -> None:
        """A changed converter retries applied/rejected rows but skips a missing PNG."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_run, scope, candidates = self._write_run_fixture(root)
            run_dir = root / "resume"
            run_dir.mkdir()
            with redirect_stdout(io.StringIO()):
                logger = EventLogger(run_dir / "events.jsonl", color="never")
                inventory, totals = _resume_inventory_from_run(
                    source_run_dir=source_run,
                    run_dir=run_dir,
                    catalog_snapshot_id="catalog",
                    source_site_id="site",
                    category_key="9",
                    theme_titles=["Трапеция"],
                    scope=scope,
                    converter_fingerprint="new-converter",
                    template_fingerprint="template",
                    logger=logger,
                )
                logger.close()
            remaining = inventory["group-id"].candidates
            self.assertEqual(
                [candidate.stable_key for candidate in remaining],
                [
                    candidates[0].stable_key,
                    candidates[1].stable_key,
                    candidates[3].stable_key,
                ],
            )
            self.assertEqual(totals["resume_skipped_missing_source"], 1)
            self.assertEqual(totals["resume_skipped_applied"], 0)
            self.assertFalse(json.loads((run_dir / "resume.json").read_text())["same_renderer"])

    def test_resume_same_renderer_skips_applied_and_rejected(self) -> None:
        """An unchanged renderer resumes only transient failures."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_run, scope, candidates = self._write_run_fixture(root)
            run_dir = root / "resume"
            run_dir.mkdir()
            with redirect_stdout(io.StringIO()):
                logger = EventLogger(run_dir / "events.jsonl", color="never")
                inventory, totals = _resume_inventory_from_run(
                    source_run_dir=source_run,
                    run_dir=run_dir,
                    catalog_snapshot_id="catalog",
                    source_site_id="site",
                    category_key="9",
                    theme_titles=["Трапеция"],
                    scope=scope,
                    converter_fingerprint="old-converter",
                    template_fingerprint="template",
                    logger=logger,
                )
                logger.close()
            self.assertEqual(
                [candidate.stable_key for candidate in inventory["group-id"].candidates],
                [candidates[3].stable_key],
            )
            self.assertEqual(totals["resume_skipped_applied"], 1)
            self.assertEqual(totals["resume_skipped_rejected_same_renderer"], 1)
            self.assertEqual(totals["resume_skipped_missing_source"], 1)

    def test_resume_changed_renderer_can_preserve_applied_assets(self) -> None:
        """A renderer fix retries rejected assets without replacing prior successes."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_run, scope, candidates = self._write_run_fixture(root)
            run_dir = root / "resume"
            run_dir.mkdir()
            with redirect_stdout(io.StringIO()):
                logger = EventLogger(run_dir / "events.jsonl", color="never")
                inventory, totals = _resume_inventory_from_run(
                    source_run_dir=source_run,
                    run_dir=run_dir,
                    catalog_snapshot_id="catalog",
                    source_site_id="site",
                    category_key="9",
                    theme_titles=["Трапеция"],
                    scope=scope,
                    converter_fingerprint="new-converter",
                    template_fingerprint="template",
                    preserve_applied=True,
                    logger=logger,
                )
                logger.close()

            self.assertEqual(
                [candidate.stable_key for candidate in inventory["group-id"].candidates],
                [candidates[1].stable_key, candidates[3].stable_key],
            )
            self.assertEqual(totals["resume_skipped_applied"], 1)
            self.assertEqual(totals["resume_skipped_missing_source"], 1)
            self.assertEqual(totals["resume_remaining_assets"], 2)

    def test_rollback_manifest_contains_only_successful_replacements(self) -> None:
        """Rollback selects the exact applied SourceAsset and ignores all attempts."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_run, scope, candidates = self._write_run_fixture(root)
            run_dir = root / "rollback"
            run_dir.mkdir()
            with redirect_stdout(io.StringIO()):
                logger = EventLogger(run_dir / "events.jsonl", color="never")
                rollback, totals = _rollback_inventory_from_run(
                    source_run_dir=source_run,
                    run_dir=run_dir,
                    catalog_snapshot_id="catalog",
                    source_site_id="site",
                    category_key="9",
                    theme_titles=["Трапеция"],
                    scope=scope,
                    logger=logger,
                )
                logger.close()
            self.assertEqual(totals["rollback_targets"], 1)
            self.assertEqual(rollback["group-id"][0].candidate, candidates[0])
            manifest = json.loads((run_dir / "rollback.json").read_text())
            self.assertEqual(manifest["target_count"], 1)

    def test_rollback_executor_sends_exact_guard_without_discovery(self) -> None:
        """Rollback calls one guarded MCP mutation and records its compact result."""

        theme = ThemeScope("Трапеция", "theme", "284", 2, 1, 4)
        group = GroupScope("group", "27556", 0)
        candidate = AssetCandidate(
            theme_title=theme.title,
            snapshot_theme_id=theme.snapshot_theme_id,
            theme_order_index=theme.order_index,
            source_group_id=group.source_group_id,
            group_key=group.group_key,
            group_order_index=group.order_index,
            problem_id=str(uuid4()),
            source_problem_id="101",
            problem_order_index=0,
            asset_key="image_1",
            sections=("condition",),
            expected_vertices=4,
        )
        source_asset_id = str(uuid4())
        item = RollbackCandidate(
            candidate=candidate,
            transformation_target_id="asset:target",
            source_asset_id=source_asset_id,
            output_sha256="a" * 64,
        )
        client = FakeMcpClient(
            {
                "delete_problem_transformation": [
                    {
                        "problem_id": candidate.problem_id,
                        "deleted_transformation_target_id": "asset:target",
                        "reopened_stages": ["assets"],
                    }
                ]
            }
        )
        args = SimpleNamespace(
            batch_size=10,
            batch_pause_seconds=0,
            max_tasks=None,
            stop_after_batches=None,
            max_asset_errors=0,
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with redirect_stdout(io.StringIO()):
                logger = EventLogger(run_dir / "events.jsonl", color="never")
                totals = Counter()
                tasks, batches, stopped = _execute_rollback(
                    client,
                    scope=[(theme, [group])],
                    rollback_by_group={group.source_group_id: [item]},
                    totals=totals,
                    args=args,
                    run_dir=run_dir,
                    logger=logger,
                )
                logger.close()
        self.assertEqual((tasks, batches, stopped), (1, 1, False))
        self.assertEqual(totals["assets_rolled_back"], 1)
        self.assertEqual(
            client.calls,
            [
                (
                    "delete_problem_transformation",
                    {
                        "problem_id": candidate.problem_id,
                        "transformation_target_id": "asset:target",
                        "expected_source_asset_id": source_asset_id,
                    },
                )
            ],
        )

    def test_missing_download_is_a_non_fatal_stale_candidate(self) -> None:
        """HTTP 404 from the stable public asset URL skips one task."""

        candidate = AssetCandidate(
            theme_title="Треугольник",
            snapshot_theme_id="theme",
            theme_order_index=3,
            source_group_id="group",
            group_key="27543",
            group_order_index=0,
            problem_id=str(uuid4()),
            source_problem_id="101",
            problem_order_index=0,
            asset_key="image_1",
            sections=("condition",),
            expected_vertices=3,
        )
        response = httpx.Response(
            404,
            request=httpx.Request("GET", "https://example.test/problem-assets/id/content"),
        )
        error = httpx.HTTPStatusError(
            "404 Not Found",
            request=response.request,
            response=response,
        )
        client = FakeMcpClient(
            {
                "get_asset": [
                    {
                        "asset_id": "current-asset",
                        "content_type": "image/png",
                        "sha256": "",
                        "size_bytes": None,
                    }
                ],
                "get_asset_file": [
                    {
                        "asset_id": "current-asset",
                        "content_type": "image/png",
                        "url": "/assets/current-asset",
                    }
                ],
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            with redirect_stdout(io.StringIO()):
                logger = EventLogger(run_dir / "events.jsonl", color="never")
                with (
                    patch(
                        "solution_runner.converters.mcp_grid_polygon_transformations.refresh_candidate",
                        return_value=RefreshedAsset(
                            "asset:target",
                            {"asset_id": "current-asset"},
                            {},
                        ),
                    ),
                    patch(
                        "solution_runner.converters.mcp_grid_polygon_transformations._transfer_get",
                        side_effect=error,
                    ),
                    self.assertRaisesRegex(CandidateStale, "HTTP 404"),
                ):
                    prepare_candidate(
                        client,
                        candidate=candidate,
                        converter=object(),
                        converter_fingerprint="fingerprint",
                        template_path=run_dir / "template.svg",
                        run_dir=run_dir,
                        transfer_timeout_seconds=1,
                        logger=logger,
                    )
                logger.close()

    def test_console_shows_group_scan_but_hides_technical_events(self) -> None:
        """Human output stays focused on groups while JSONL keeps diagnostics."""

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "events.jsonl"
            output = io.StringIO()
            with redirect_stdout(output):
                logger = EventLogger(path, color="always")
                logger.emit("mcp_ready", role="admin")
                logger.emit(
                    "mcp_retry",
                    level="warning",
                    tool="list_source_parser_targets",
                    reason="temporary",
                )
                logger.emit(
                    "worklist_group_scan_start",
                    theme="Трапеция",
                    group_key="27556",
                    position=1,
                    total_groups=39,
                )
                logger.emit(
                    "worklist_group_scanned",
                    theme="Трапеция",
                    group_key="27556",
                    position=1,
                    total_groups=39,
                    tasks=52,
                )
                logger.close()
            console = output.getvalue()
            self.assertNotIn("mcp_ready", console)
            self.assertNotIn("mcp_retry", console)
            self.assertNotIn("list_source_parser_targets", console)
            self.assertIn("СКАНИРУЮ ГРУППУ 1/39", console)
            self.assertIn("ГРУППА ПРОСКАНИРОВАНА 1/39", console)
            persisted = path.read_text(encoding="utf-8")
            self.assertIn('"event": "mcp_retry"', persisted)

    def test_inventory_selects_only_non_rejected_rasters(self) -> None:
        """PNG/BMP enter while SVG, rejected, and non-ready problems stay out."""

        theme = ThemeScope("Трапеция", "theme", "284", 2, 1, 4)
        group = GroupScope("group", "27556", 0)
        client = FakeMcpClient(
            {
                "get_source_catalog_children": [
                    {
                        "items": [
                            {"uuid": "p1", "name": "Задача 1"},
                            {"uuid": "p2", "name": "Задача 2"},
                            {"uuid": "p3", "name": "Задача 3"},
                            {"uuid": "p4", "name": "Задача 4"},
                        ]
                    }
                ],
                "get_problem_pipeline_state": [
                    {"problem_id": "p1", "statuses": {"normalized": "ready"}},
                    {"problem_id": "p2", "statuses": {"normalized": "rejected"}},
                    {"problem_id": "p3", "statuses": {"normalized": "ready"}},
                    {"problem_id": "p4", "statuses": {"normalized": "ready"}},
                ],
                "get_source_catalog_section_images": [
                    {
                        "scope": {
                            "catalog_snapshot_id": "catalog",
                            "source_group_ids": ["group"],
                        },
                        "concrete_problem_count": 4,
                        "condition": {
                            "problems": [
                                {
                                    "source_problem_id": "1",
                                    "images": [
                                        {
                                            "asset_key": "formula_1",
                                            "kind": "formula_image",
                                            "content_type": "image/png",
                                        },
                                        {
                                            "asset_key": "image_1",
                                            "kind": "ordinary_image",
                                            "content_type": "image/png",
                                        }
                                    ],
                                },
                                {
                                    "source_problem_id": "2",
                                    "images": [
                                        {
                                            "asset_key": "image_1",
                                            "kind": "ordinary_image",
                                            "content_type": "image/png",
                                        }
                                    ],
                                },
                                {
                                    "source_problem_id": "3",
                                    "images": [
                                        {
                                            "asset_key": "image_1",
                                            "kind": "ordinary_image",
                                            "content_type": "image/svg+xml",
                                        }
                                    ],
                                },
                                {
                                    "source_problem_id": "4",
                                    "images": [
                                        {
                                            "asset_key": "image_1",
                                            "kind": "ordinary_image",
                                            "content_type": "image/bmp",
                                        }
                                    ],
                                },
                            ]
                        },
                        "solution": {"problems": []},
                    }
                ],
            }
        )
        inventory = build_group_inventory(
            client, catalog_snapshot_id="catalog", theme=theme, group=group
        )
        self.assertEqual(
            [item.problem_id for item in inventory.candidates],
            ["p1", "p4"],
        )
        self.assertEqual(inventory.counts["png_tasks"], 2)
        self.assertEqual(inventory.counts["ordinary_svg_assets"], 1)
        self.assertEqual(inventory.counts["rejected_problems"], 1)
        self.assertEqual(inventory.counts["formula_or_unknown_images"], 1)
        self.assertEqual(
            [name for name, _ in client.calls],
            [
                "get_source_catalog_section_images",
                "get_source_catalog_children",
                "get_problem_pipeline_state",
                "get_problem_pipeline_state",
                "get_problem_pipeline_state",
                "get_problem_pipeline_state",
            ],
        )
        self.assertEqual(
            client.calls[0][1],
            {"target_id": "group", "target_type": "group"},
        )

    def test_refresh_candidate_uses_current_asset_target_context(self) -> None:
        """Current target inspection uses the compact replacement context tool."""

        candidate = AssetCandidate(
            "Трапеция", "theme", 2, "group", "27556", 0,
            "problem", "5217", 0, "image_1", ("condition",), 4,
        )
        current_asset = {
            "asset_key": "image_1",
            "asset_id": "asset-id",
            "kind": "ordinary_image",
            "transformation_target_id": "asset:target",
        }
        client = FakeMcpClient(
            {
                "get_problem_transformation_context": [
                    {"normalized_content": {"assets": [current_asset]}}
                ],
                "get_problem_asset_target_context": [
                    {
                        "problem_id": "problem",
                        "transformation_target_id": "asset:target",
                        "current_asset_id": "asset-id",
                        "current_asset": current_asset,
                    }
                ],
            }
        )

        refreshed = refresh_candidate(client, candidate)

        self.assertEqual(refreshed.transformation_target_id, "asset:target")
        self.assertEqual(refreshed.asset["asset_id"], "asset-id")
        self.assertEqual(client.calls[-1][0], "get_problem_asset_target_context")

    def test_apply_verifies_current_readback_asset_metadata(self) -> None:
        """Replacement readback resolves SVG type and digest from the asset UUID."""

        candidate = AssetCandidate(
            "Трапеция", "theme", 2, "group", "27556", 0,
            "problem", "5217", 0, "image_1", ("condition",), 4,
        )
        svg_bytes = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>'
        digest = hashlib.sha256(svg_bytes).hexdigest()
        source_asset_id = str(uuid4())
        client = FakeMcpClient(
            {
                "prepare_source_asset_upload": [{"method": "PUT"}],
                "get_source_asset": [{
                    "source_asset": {
                        "source_asset_id": source_asset_id,
                        "canonical_asset_key": "canonical",
                        "content_type": "image/svg+xml",
                        "sha256": digest,
                    }
                }],
                "replace_problem_asset": [{"cleanup_candidate_asset_id": None}],
                "get_problem_asset_target_context": [{
                    "current_asset_id": source_asset_id,
                    "current_asset": {
                        "asset_id": source_asset_id,
                        "asset_key": "image_1",
                        "kind": "ordinary_image",
                        "alt": "[(1, 1), (2, 1), (2, 2), (1, 2)]",
                    },
                }],
                "get_asset": [{
                    "asset_id": source_asset_id,
                    "content_type": "image/svg+xml",
                    "sha256": digest,
                }],
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            svg_path = root / "asset.svg"
            svg_path.write_bytes(svg_bytes)
            prepared = PreparedAsset(
                candidate=candidate,
                transformation_target_id="asset:image_1",
                input_sha256="a" * 64,
                input_size_bytes=1,
                output_sha256=digest,
                output_size_bytes=len(svg_bytes),
                canonical_asset_key="canonical",
                alt_text="[(1, 1), (2, 1), (2, 2), (1, 2)]",
                input_path=root / "input.png",
                svg_path=svg_path,
                diagnostic_path=root / "asset.txt",
                validation={},
            )
            with (
                redirect_stdout(io.StringIO()),
                patch(
                    "solution_runner.converters.mcp_grid_polygon_transformations._transfer_put",
                    return_value={"source_asset_id": source_asset_id, "sha256": digest},
                ),
            ):
                logger = EventLogger(root / "events.jsonl", color="never")
                result = apply_prepared_asset(
                    client,
                    source_site_id="site",
                    prepared=prepared,
                    transfer_timeout_seconds=1,
                    logger=logger,
                )
                logger.close()

        self.assertEqual(result[0], source_asset_id)
        replace_call = next(call for call in client.calls if call[0] == "replace_problem_asset")
        self.assertEqual(replace_call[1]["replacement_asset_id"], source_asset_id)
        self.assertNotIn("replacement_source_asset_id", replace_call[1])

    def test_fixed_theme_scope_skips_catalog_tree(self) -> None:
        """Known immutable theme and group UUIDs require no discovery MCP calls."""

        calls = []

        class ScopeClient:
            def call(self, name: str, arguments=None, *, attempts: int = 3):
                del attempts
                calls.append((name, arguments))
                raise AssertionError(f"unexpected MCP call: {name}")

        with tempfile.TemporaryDirectory() as temporary:
            with redirect_stdout(io.StringIO()):
                logger = EventLogger(Path(temporary) / "events.jsonl", color="never")
                _, scope = discover_catalog_scope(
                    ScopeClient(),
                    catalog_snapshot_id="4073fc7b-2056-4697-b18b-38741c94d0f4",
                    category_key="9",
                    category_title="9. Задачи на квадратной решетке",
                    theme_titles=["Ромб"],
                    logger=logger,
                )
                logger.close()
        self.assertEqual(calls, [])
        self.assertEqual(scope[0][0].snapshot_theme_id, "785f5813-b3f0-41cd-b6a1-6c63c4223d5e")
        self.assertEqual(scope[0][1][0].group_key, "244983")
        self.assertEqual(
            scope[0][1][0].source_group_id,
            "c7fb645b-bb12-48f9-86c9-de6bd980389e",
        )

    def test_fixed_scope_can_select_one_exact_group_key(self) -> None:
        """An explicit group key keeps the run inside one configured source group."""

        with tempfile.TemporaryDirectory() as temporary:
            with redirect_stdout(io.StringIO()):
                logger = EventLogger(Path(temporary) / "events.jsonl", color="never")
                _, scope = discover_catalog_scope(
                    FakeMcpClient({}),
                    catalog_snapshot_id="4073fc7b-2056-4697-b18b-38741c94d0f4",
                    category_key="9",
                    category_title="9. Задачи на квадратной решетке",
                    theme_titles=["Трапеция"],
                    group_keys=["27556"],
                    logger=logger,
                )
                logger.close()

        self.assertEqual([group.group_key for group in scope[0][1]], ["27556"])

    def test_diagnostics_require_theme_vertex_count(self) -> None:
        """A triangle result is rejected for a four-vertex theme."""

        diagnostics = {
            "grid_source": "alpha",
            "alpha_grid_x_step": 20.0,
            "alpha_grid_y_step": 20.1,
            "source_quad_before_snap": [(0, 0), (20, 0), (0, 20)],
            "source_quad_on_alpha_grid": [(0, 0), (20, 0), (0, 20.1)],
            "source_polygon_points": [(0, 0), (1, 0), (0, 1)],
            "grid_indices": [(0, 0), (1, 0), (0, 1)],
            "svg_size": (100, 100),
        }
        with self.assertRaisesRegex(CandidateRejected, "requires 4"):
            _validate_diagnostics(
                diagnostics, theme_title="Трапеция", expected_vertices=4
            )

    def test_diagnostics_use_ordered_grid_vertices_for_area(self) -> None:
        """Display-sorted points cannot turn a valid trapezoid into zero area."""

        diagnostics = {
            "grid_source": "grayscale",
            "alpha_grid_x_step": 20.0,
            "alpha_grid_y_step": 20.0,
            "source_quad_before_snap": [(40, 20), (120, 20), (200, 120), (20, 120)],
            "source_quad_on_alpha_grid": [(40, 20), (120, 20), (200, 120), (20, 120)],
            "source_polygon_points": [(1, 1), (5, 1), (0, 6), (9, 6)],
            "grid_indices": [(1, 1), (5, 1), (9, 6), (0, 6)],
            "svg_size": (260, 180),
        }
        result = _validate_diagnostics(
            diagnostics, theme_title="Трапеция", expected_vertices=4
        )
        self.assertGreater(result["polygon_area_cells"], 0)

    def test_grayscale_mask_ignores_connected_grid(self) -> None:
        """A solid trapezoid wins over the full-page grayscale lattice."""

        height, width = 180, 246
        rgb = np.full((height, width, 3), 255, dtype=np.uint8)
        for x in range(11, 232, 20):
            cv2.line(rgb, (x, 11), (x, 171), (187, 187, 187), 1)
        for y in range(11, 172, 20):
            cv2.line(rgb, (11, y), (231, y), (187, 187, 187), 1)
        polygon = np.asarray([(51, 31), (131, 31), (211, 131), (31, 131)], np.int32)
        cv2.fillPoly(rgb, [polygon], (169, 169, 169))
        cv2.polylines(rgb, [polygon], True, (79, 79, 79), 2)
        rgba = np.dstack([rgb, np.full((height, width), 255, dtype=np.uint8)])

        mask, info = grayscale_shape_mask(rgba)
        x1, y1, x2, y2 = info["alpha_shape_bbox"]
        self.assertGreater(x1, 20)
        self.assertGreater(y1, 20)
        self.assertLess(x2, 220)
        self.assertLess(y2, 145)
        self.assertEqual(len(quad_from_mask(mask, width=width, height=height)), 4)

    def test_triangle_profile_ignores_small_raster_corner(self) -> None:
        """A skinny triangle stays triangular despite a four-point pixel hull."""

        height, width = 260, 150
        mask = np.zeros((height, width), dtype=np.uint8)
        raster_hull = np.asarray(
            [(65, 64), (122, 235), (65, 236), (63, 233)],
            dtype=np.int32,
        )
        cv2.fillPoly(mask, [raster_hull], 255)

        points = quad_from_mask(
            mask,
            width=width,
            height=height,
            expected_vertices=3,
        )

        self.assertEqual(len(points), 3)

    def test_quadrilateral_profile_preserves_dart_reflex_vertex(self) -> None:
        """A thin concave dart must not replace its notch with two hull pixels."""

        height, width = 296, 300
        mask = np.zeros((height, width), dtype=np.uint8)
        polygon = np.asarray(
            [(64, 60), (172, 117), (65, 176), (235, 119)],
            dtype=np.int32,
        )
        cv2.fillPoly(mask, [polygon], 255)

        points = quad_from_mask(
            mask,
            width=width,
            height=height,
            expected_vertices=4,
        )

        self.assertEqual(len(points), 4)
        self.assertTrue(
            any(abs(x - 172) <= 2 and abs(y - 117) <= 2 for x, y in points)
        )

    def test_quadrilateral_profile_preserves_kite_reflex_vertex(self) -> None:
        """A concave kite whose hull is triangular must retain four vertices."""

        height, width = 580, 468
        mask = np.zeros((height, width), dtype=np.uint8)
        polygon = np.asarray(
            [(405, 60), (243, 116), (64, 61), (232, 459)],
            dtype=np.int32,
        )
        cv2.fillPoly(mask, [polygon], 255)

        points = quad_from_mask(
            mask,
            width=width,
            height=height,
            expected_vertices=4,
        )

        self.assertEqual(len(points), 4)
        self.assertTrue(
            any(abs(x - 243) <= 2 and abs(y - 116) <= 2 for x, y in points)
        )

    def test_empty_polygon_has_explicit_grid_selection_error(self) -> None:
        """Missing polygon vertices must not leak a generic max-empty failure."""

        grid = {
            "source": "alpha",
            "confidence": 1.0,
            "x": {"origin": 0.0, "step": 20.0},
            "y": {"origin": 0.0, "step": 20.0},
        }

        with self.assertRaisesRegex(ValueError, "polygon_vertices_not_found"):
            _select_grid_for_quad([], [grid])

    def test_determinism_render_reuses_candidate_vertex_count(self) -> None:
        """The verification render must use the same geometry profile as preparation."""

        candidate = AssetCandidate(
            theme_title="Треугольник",
            snapshot_theme_id="theme-id",
            theme_order_index=3,
            source_group_id="group-id",
            group_key="27543",
            group_order_index=0,
            problem_id=str(uuid4()),
            source_problem_id="246385",
            problem_order_index=1,
            asset_key="image_1",
            sections=("condition",),
            expected_vertices=3,
        )

        class RecordingConverter:
            """Write deterministic fixtures and retain the requested vertex count."""

            def __init__(self) -> None:
                self.expected_vertices = None

            def run(self, source, output_dir, *args, **kwargs):
                del source, args
                self.expected_vertices = kwargs.get("expected_vertices")
                output = Path(output_dir) / "check.svg"
                output.write_bytes(b"<svg />")
                output.with_suffix(".txt").write_bytes(b"diagnostics")
                return output

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "input.png"
            svg_path = root / "prepared.svg"
            diagnostic_path = root / "prepared.txt"
            input_path.write_bytes(b"png")
            svg_path.write_bytes(b"<svg />")
            diagnostic_path.write_bytes(b"diagnostics")
            prepared = PreparedAsset(
                candidate=candidate,
                transformation_target_id="asset:image_1",
                input_sha256="a" * 64,
                input_size_bytes=3,
                output_sha256="b" * 64,
                output_size_bytes=7,
                canonical_asset_key="canonical",
                alt_text="[(1, 2), (2, 2), (1, 5)]",
                input_path=input_path,
                svg_path=svg_path,
                diagnostic_path=diagnostic_path,
                validation={},
            )
            converter = RecordingConverter()

            verify_first_deterministic_render(
                prepared,
                converter=converter,
                template_path=root / "template.svg",
                run_dir=root,
            )

        self.assertEqual(converter.expected_vertices, 3)

    def test_alpha_triplet_bands_promote_the_third_harmonic(self) -> None:
        """Three alpha bands per line resolve to the square grid's fundamental step."""

        centers = [
            5.49,
            15.0,
            56.0,
            65.46,
            74.99,
            112.01,
            121.50,
            131.0,
            168.0,
            177.51,
            187.0,
            224.0,
            233.52,
            243.0,
            280.0,
            289.51,
            298.50,
        ]
        base = _fit_grid_axis(centers, 300)
        promoted, multiplier = _promote_clean_grid_fundamental(centers, 300, base)
        self.assertEqual(multiplier, 3)
        self.assertAlmostEqual(promoted["step"], 55.2, delta=1.0)

    def test_problem_batches_never_split_assets_of_one_problem(self) -> None:
        """Batch size counts tasks while preserving all their PNG assets."""

        candidates = []
        for index, problem_id in enumerate(("p1", "p1", "p2", "p3")):
            candidates.append(
                AssetCandidate(
                    "Треугольник",
                    "theme",
                    3,
                    "group",
                    "g",
                    0,
                    problem_id,
                    str(index),
                    index,
                    f"image_{index}",
                    ("condition",),
                    3,
                )
            )
        batches = list(_problem_batches(candidates, 2))
        self.assertEqual([[item.problem_id for item in batch] for batch in batches], [
            ["p1", "p1", "p2"],
            ["p3"],
        ])

    def test_canonical_key_depends_on_code_and_output(self) -> None:
        """Reusable keys are stable yet version-sensitive."""

        first = _canonical_asset_key("a" * 64, "b" * 64)
        self.assertEqual(first, _canonical_asset_key("a" * 64, "b" * 64))
        self.assertNotEqual(first, _canonical_asset_key("c" * 64, "b" * 64))
        self.assertNotEqual(first, _canonical_asset_key("a" * 64, "d" * 64))
        self.assertLessEqual(len(first), 160)


if __name__ == "__main__":
    unittest.main()
