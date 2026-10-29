import json
import sqlite3
from threading import Event

import pytest

from solution_runner.dashboard.job_queue import DurableJobQueue
from solution_runner.dashboard.process_logs import run_logged


class Manager:
    store = None
    on_complete = None

    def __init__(self):
        self.calls = []
        self.states = {}

    def get(self, group):
        return self.states.get(group)

    def _write(self, state):
        self.states[state['group_key']] = state

    def run(self, group, mode='all', **kwargs):
        self.calls.append((group, mode, kwargs))
        return {'status': 'completed'}


def seed(queue, kind, group, status):
    with sqlite3.connect(queue.database) as connection:
        connection.execute(
            "INSERT INTO dashboard_jobs(kind,payload,status,created_at) VALUES (?,?,?,'2020-01-01')",
            (kind, json.dumps({'args': [group, 'all'], 'kwargs': {}}), status),
        )


def test_restart_recovers_queued_jobs_in_order_and_not_running_jobs(tmp_path):
    manager = Manager()
    queue = DurableJobQueue(tmp_path / 'state.sqlite3')
    queue.register('dry-run', manager.run)
    manager.states['interrupted'] = {'group_key': 'interrupted', 'status': 'running'}
    seed(queue, 'dry-run', 'interrupted', 'running')
    seed(queue, 'dry-run', 'first', 'queued')
    seed(queue, 'dry-run', 'second', 'queued')
    completed = []
    manager.on_complete = lambda group, result: completed.append(group)
    queue.start()
    queue.shutdown()
    assert [call[0] for call in manager.calls] == ['first', 'second']
    assert completed == ['first', 'second']
    assert manager.states['interrupted']['status'] == 'failed'
    assert [row['status'] for row in queue.list_jobs()] == ['completed', 'completed', 'interrupted']


def test_queue_serializes_work_and_keeps_cancelled_pending_work(tmp_path):
    gate = Event()
    running = Event()

    class BlockingManager(Manager):
        def run(self, group, mode='all', **kwargs):
            running.set()
            assert gate.wait(5)
            return super().run(group, mode, **kwargs)

    manager = BlockingManager()
    original = manager.run
    queue = DurableJobQueue(tmp_path / 'state.sqlite3')
    queue.register('dry-run', manager.run)
    queue.start()
    first = queue.submit(manager.run, 'first')
    assert running.wait(5)
    second = queue.submit(manager.run, 'second')
    assert second.cancel()
    gate.set()
    first.result(timeout=5)
    queue.shutdown()
    assert manager.calls == [('first', 'all', {})]
    recovered = DurableJobQueue(queue.database)
    recovered.register('dry-run', original)
    recovered.start()
    recovered.shutdown()
    assert [call[0] for call in manager.calls] == ['first', 'second']


def test_two_dashboard_processes_cannot_own_the_queue(tmp_path):
    queue = DurableJobQueue(tmp_path / 'state.sqlite3')
    try:
        with pytest.raises(RuntimeError, match='another dashboard'):
            DurableJobQueue(queue.database)
    finally:
        queue.shutdown()


def test_apply_approval_rechecked_after_restart(tmp_path):
    class ApplyManager(Manager):
        def _verified_group(self, group):
            raise ValueError('approval revoked')

    manager = ApplyManager()
    manager.states['123'] = {'group_key': '123', 'status': 'queued'}
    queue = DurableJobQueue(tmp_path / 'state.sqlite3')
    queue.register('apply-group', manager.run)
    seed(queue, 'apply-group', '123', 'queued')
    queue.start()
    queue.shutdown()
    assert not manager.calls
    assert queue.list_jobs()[0]['status'] == 'failed'
    assert 'approval revoked' in queue.log_tail(1)
    assert manager.states['123']['status'] == 'failed'


def test_launcher_output_is_saved_to_job_log(tmp_path):
    import sys

    class LoggingManager(Manager):
        def run(self, group):
            code = run_logged([sys.executable, '-c', "import sys; print('stdout'); print('stderr', file=sys.stderr)"])
            return {'status': 'completed' if code == 0 else 'failed'}

    manager = LoggingManager()
    queue = DurableJobQueue(tmp_path / 'state.sqlite3')
    queue.register('dry-run', manager.run)
    queue.start()
    queue.submit(manager.run, '123').result(timeout=5)
    queue.shutdown()
    assert 'stdout' in queue.log_tail(1)
    assert 'stderr' in queue.log_tail(1)
    with pytest.raises(KeyError):
        queue.log_tail(99)


def test_missing_handler_leaves_queued_work_for_configured_restart(tmp_path):
    queue = DurableJobQueue(tmp_path / 'state.sqlite3')
    seed(queue, 'dry-run', '123', 'queued')
    queue.start()
    queue.shutdown()
    assert queue.list_jobs()[0]['status'] == 'queued'


def test_legacy_running_state_does_not_leave_group_stuck(tmp_path):
    manager = Manager()
    manager.state_dir = tmp_path / 'dry-runs'
    manager.state_dir.mkdir()
    (manager.state_dir / '123.json').write_text('{}')
    manager.states['123'] = {'group_key': '123', 'mode': 'all', 'status': 'running'}
    queue = DurableJobQueue(tmp_path / 'state.sqlite3')
    queue.register('dry-run', manager.run)
    queue.start()
    queue.shutdown()
    assert manager.states['123']['status'] == 'failed'
    assert 'No durable job' in manager.states['123']['error']
    assert not manager.calls


def test_history_filters_group_before_limiting(tmp_path):
    queue = DurableJobQueue(tmp_path / 'state.sqlite3')
    seed(queue, 'dry-run', 'wanted', 'completed')
    seed(queue, 'dry-run', 'other', 'completed')
    assert queue.list_jobs(limit=1, group_key='wanted')[0]['payload']['args'][0] == 'wanted'
    queue.shutdown()
