from concurrent.futures import ThreadPoolExecutor

from solution_runner.dashboard.applies import ApplyManager
from solution_runner.dashboard.dry_runs import DryRunManager


def test_dry_runs_and_applies_can_share_one_background_queue(tmp_path):
    queue = ThreadPoolExecutor(max_workers=1)
    try:
        dry_runs = DryRunManager(
            var_dir=tmp_path,
            profiles={},
            gateway_factory=lambda: None,
            background_executor=queue,
        )
        applies = ApplyManager(
            var_dir=tmp_path,
            profiles={},
            inventory_store=object(),
            background_executor=queue,
        )

        assert dry_runs.executor is queue
        assert applies.executor is queue
    finally:
        queue.shutdown()
