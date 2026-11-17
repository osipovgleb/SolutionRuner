"""Verify parent asset identity and update the Helpers stage."""

from .content_gateway import RightTriangleGateway
from .errors import ContentPlanError as RightTrianglePlanError
from .models import GroupProfile


def _helpers_update(gateway: RightTriangleGateway, problem_id: str) -> None:
    """Set the verified P2–P5/P6 terminal branches and validate setter readback."""

    state = gateway.get_problem_pipeline_state(problem_id)
    current_helpers = (state.get("stage_details") or {}).get("helpers")
    if (
        isinstance(current_helpers, dict)
        and current_helpers.get("helpers_status") == "ready"
    ):
        return
    token = (state.get("stage_state_tokens") or {}).get("helpers")
    if not isinstance(token, str) or not token:
        raise RightTrianglePlanError("Helpers token is unavailable")
    branches = {
        **{
            branch: {"status": "ready", "revision": 2, "attempted_revision": 2}
            for branch in ("p2", "p3", "p4", "p5")
        },
        "p6": {"status": "not_required", "revision": 1, "attempted_revision": 1},
    }
    response = gateway.set_problem_pipeline_stage_state_batch(
        "helpers",
        [
            {
                "problem_id": problem_id,
                "expected_stage_state_token": token,
                "values": {"operation": "set_branches", "branches": branches},
            }
        ],
        "Verified right-triangle condition asset, solution, and answer",
    )
    results = response.get("results")
    if not isinstance(results, list) or len(results) != 1:
        raise RightTrianglePlanError("Helpers setter omitted single-target readback")
    values = results[0].get("values") if isinstance(results[0], dict) else None
    if not isinstance(values, dict) or values.get("helpers_status") != "ready":
        raise RightTrianglePlanError("Helpers readback is not ready")


def _pinned_condition_asset_id(
    gateway: RightTriangleGateway, profile: GroupProfile
) -> str | None:
    """Verify and return a profile-owned shared condition asset when configured."""

    asset_id = profile.condition_asset_id
    if asset_id is None:
        return None
    expected_sha256 = profile.condition_asset_sha256
    if not expected_sha256:
        raise RightTrianglePlanError("pinned condition asset digest is missing")
    payload = gateway.get_source_asset(asset_id)
    source_asset = payload.get("source_asset") if isinstance(payload, dict) else None
    if (
        not isinstance(source_asset, dict)
        or source_asset.get("source_asset_id") != asset_id
        or str(source_asset.get("sha256") or "").lower() != expected_sha256
        or str(source_asset.get("content_type") or "").split(";", 1)[0].lower()
        != "image/svg+xml"
    ):
        raise RightTrianglePlanError("pinned condition asset readback drifted")
    return asset_id
