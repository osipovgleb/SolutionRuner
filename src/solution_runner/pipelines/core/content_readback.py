"""Verify that frozen content repairs survived authoritative readback."""

from typing import Any

from bs4 import BeautifulSoup

from .errors import ContentPlanError as RightTrianglePlanError


def _presentation_html(raw: str) -> str:
    """Compare authoritative condition HTML without transient target annotations."""
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup.find_all(True):
        tag.attrs.pop("data-transformation-target-id", None)
    return str(soup)


def _validate_frozen_presentation(frozen: list[dict[str, Any]]) -> None:
    """Restrict presentation-only repairs to the reviewed condition targets."""

    for item in frozen:
        target = str(item.get("transformation_target_id") or "")
        if not (
            (
                target.startswith("section:condition:")
                and item.get("operation") == "rewrite"
            )
            or (target.startswith("asset:") and item.get("operation") == "remove")
        ):
            raise RightTrianglePlanError(
                "presentation rule may only rewrite the condition"
            )


def _check_readback_sections(
    context: dict[str, Any], refreshed: dict[str, Any], frozen: list[dict[str, Any]]
) -> None:
    """Verify repaired section HTML and retain unrelated sections exactly."""

    before_sections = (context.get("normalized_content") or {}).get("sections", [])
    after_sections = (refreshed.get("normalized_content") or {}).get("sections", [])
    touched = set()
    for item in frozen:
        if str(item.get("transformation_target_id", "")).startswith("section:"):
            key = item["transformation_target_id"].split(":")[1]
            touched.add(key)
            actual = next(
                (
                    section.get("html", "")
                    for section in after_sections
                    if section.get("key") == key
                ),
                "",
            )
            if _presentation_html(actual) != _presentation_html(item["value"]["html"]):
                raise RightTrianglePlanError(
                    "section readback differs from frozen content"
                )
    if [item for item in before_sections if item.get("key") not in touched] != [
        item for item in after_sections if item.get("key") not in touched
    ]:
        raise RightTrianglePlanError("unrelated sections changed during content repair")
