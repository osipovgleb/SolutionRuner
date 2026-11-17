"""Dashboard deletion and update HTTP routes."""


class DashboardUpdateRoutes:
    def do_DELETE(self) -> None:
        segments = self._segments()
        if len(segments) != 3 or segments[:2] != ["api", "groups"]:
            self._json(404, {"error": "not_found"})
            return
        group_key = segments[2]
        group = self._group_payload(self.server.store.get_group(group_key))
        if group is None:
            self._json(404, {"error": "group_not_found"})
            return
        initialization = (
            self.server.initializer.get(group_key) if self.server.initializer else {}
        )
        if (
            group.get("job")
            or group.get("agent_status") in {"working", "verifying"}
            or initialization.get("status") in {"pending", "running"}
        ):
            self._json(409, {"error": "group_is_running"})
            return
        self.server.store.remove_group(group_key)
        self._json(200, {"removed": True})

    def do_PATCH(self) -> None:
        segments = self._segments()
        if len(segments) != 3 or segments[:2] != ["api", "groups"]:
            self._json(404, {"error": "not_found"})
            return
        body = self._body()
        if body.get("column") not in {
            None,
            "initialization",
            "queue",
            "work",
            "review",
            "issues",
            "done",
        }:
            self._json(400, {"error": "invalid_column"})
            return
        editable = {
            "column",
            "title",
            "task_title",
            "task_url",
            "revision_requested",
            "existing_solution_policy",
            "condition_image_policy",
            "solution_image_policy",
            "verify_answers",
            "verify_helpers",
            "agent_sample_size",
        }
        changes = {key: value for key, value in body.items() if key in editable}
        group = self._group_payload(
            self.server.store.update_group(segments[2], changes)
        )
        self._json(200, group) if group else self._json(
            404, {"error": "group_not_found"}
        )
