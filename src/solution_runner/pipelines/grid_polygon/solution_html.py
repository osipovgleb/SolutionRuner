"""Render and inspect image references in generated solution HTML."""

import re
from html import escape


def _centered_asset_html(
    *,
    asset_key: str,
    source_asset_id: str,
    asset_url: str,
    alt_text: str,
) -> str:
    """Build one centered solution image placed before explanation prose."""

    target = f"asset:{asset_key}"
    return (
        f'<center><img src="{escape(asset_url, quote=True)}" '
        f'alt="{escape(alt_text, quote=True)}" '
        f'data-asset-id="{escape(source_asset_id, quote=True)}" '
        f'data-asset-key="{escape(asset_key, quote=True)}" '
        f'data-transformation-target-id="{escape(target, quote=True)}"></center>'
    )


def _references_asset_key(solution_html: str, asset_key: str) -> bool:
    """Return whether final solution HTML still references one prior asset key."""

    return bool(
        re.search(
            r'\bdata-asset-key\s*=\s*["\']' + re.escape(asset_key) + r'["\']',
            solution_html,
            flags=re.IGNORECASE,
        )
    )
