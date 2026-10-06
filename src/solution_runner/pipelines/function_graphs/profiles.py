"""Audited EGE hyperbola groups; current condition images are preserved."""
from ..core.profile_definitions import _profile

PROFILES = tuple(
    _profile(
        key, group_id, index,
        catalog_snapshot_id='41bc4d03-40cd-4407-8dea-df76e3f47ea8',
        category_key='12',
        theme_title='Гиперболы',
        theme_order_index=2,
        snapshot_theme_id='4309cd49-7738-4b5a-b0d8-3892b940e5db',
        expected_vertices=None,
        strategy_key=None,
        workflow_kind='content_rule',
        content_rule_key=f'hyperbola-shift-{mode}',
        rewrite_existing_solution=True,
    )
    for key, group_id, index, mode in (
        ('508951', '84eff141-c86b-4919-bd7f-384a62eb21cf', 0, 'value'),
        ('508961', '0c1b13d3-a625-4f9d-95f4-cef5cb087a19', 1, 'argument'),
        ('508971', 'b7df39c8-06a2-46ca-b69b-a7ad420cc81e', 2, 'horizontal-value'),
        ('508983', 'bec09ca3-a236-47aa-9fcd-776884b9a05a', 3, 'horizontal-argument'),
        ('508993', 'b4a0f3c7-c5de-4c56-a003-7c236d2be077', 4, 'fractional-coefficient'),
        ('509001', '25605c37-1c45-4790-9713-6711d0b2090a', 5, 'fractional-coefficient'),
    )
)
