"""Select a dry-run target while closing any temporary gateway."""


def select_run_target(
    manager, profile, mode, excluded_problem_ids, requested_problem_id
):
    # Resolve through the caller module to preserve existing test and integration hooks.
    from .dry_runs import (
        _child_rows,
        _select_problem,
        _source_problem_id,
        load_group_inventory,
    )

    gateway = None
    try:
        if mode == "all":
            selected = None
        elif manager.inventory_store is not None:
            inventory = load_group_inventory(
                manager.inventory_store,
                profile,
                apply_solution_scope=mode not in {"parent", "problem"},
            )
            children = [
                {
                    "problem_id": target.problem_id,
                    "source_problem_id": target.source_problem_id,
                }
                for target in inventory.targets
            ]
            selected = _select_problem(
                children,
                mode,
                choose=manager.choose,
                excluded_problem_ids=excluded_problem_ids,
                requested_problem_id=requested_problem_id,
            )
        else:
            gateway = manager.gateway_factory()
            children = gateway.get_source_catalog_children(
                profile.source_group_id, "group"
            )
            if (
                mode == "random"
                and getattr(profile, "solution_scope", "all") == "missing_only"
            ):
                missing = gateway.get_source_catalog_missing_solution_summary(
                    profile.source_group_id, "group"
                )
                eligible = {
                    str(value) for value in missing.get("source_problem_ids", [])
                }
                rows = _child_rows(children)
                children = rows[:1] + [
                    item for item in rows[1:] if _source_problem_id(item) in eligible
                ]
            selected = _select_problem(
                children,
                mode,
                choose=manager.choose,
                excluded_problem_ids=excluded_problem_ids,
                requested_problem_id=requested_problem_id,
            )
        return selected
    finally:
        close = getattr(gateway, "close", None)
        if callable(close):
            close()
