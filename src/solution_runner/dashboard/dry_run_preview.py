"""Merge newly fetched dry-run samples with an existing preview."""

from .previews import load_preview


def merged_preview(preview_dir, group_key, fresh_preview, append):
    if append:
        preview = load_preview(preview_dir, group_key) or {
            "group_key": group_key,
            "samples": [],
        }
        fresh_by_id = {
            str(sample.get("problem_id")): sample
            for sample in fresh_preview.get("samples", [])
            if isinstance(sample, dict) and sample.get("problem_id")
        }
        samples = preview.setdefault("samples", [])
        preview["samples"] = [
            fresh_by_id.pop(str(sample.get("problem_id")), sample) for sample in samples
        ] + list(fresh_by_id.values())
        preview["fetched_at"] = fresh_preview["fetched_at"]
    else:
        preview = fresh_preview
    return preview
