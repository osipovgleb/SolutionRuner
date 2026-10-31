"""Completion ordering, failure propagation and no write replay in the shared client."""

from queue import Queue
from threading import Condition, Lock
from types import SimpleNamespace

import pytest

from solution_runner.dashboard.codex_transport import SharedCodexClient


def client():
    value = SharedCodexClient.__new__(SharedCodexClient)
    value._condition = Condition()
    value._write_lock = Lock()
    value._pending = {}
    value._sequence = 0
    value._completed = {}
    value._active = {}
    value._failure = None
    value._ready = Queue()
    return value


def test_completion_before_start_acknowledgement_does_not_hang():
    value = client()

    def request(method, params):
        value._completed['turn-1'] = {'id': 'turn-1', 'status': 'completed'}
        return {'turn': {'id': 'turn-1'}}

    value.request = request
    assert value.start_turn('same-thread', 'hello', 'model', 'medium') == 'turn-1'
    assert value._active == {}
    assert value.wait_turn('turn-1') == 0


def test_connection_loss_wakes_pending_requests_and_waiters():
    value = client()
    pending = Queue()
    value._pending[1] = pending
    value._fail('daemon disconnected')
    assert pending.get_nowait()['error']['message'] == 'daemon disconnected'
    with pytest.raises(RuntimeError, match='daemon disconnected'):
        value.wait_turn('unfinished')
    with pytest.raises(RuntimeError, match='daemon disconnected'):
        value.request('thread/start', {})


def test_timeout_does_not_replay_mutating_request():
    value = client()
    writes = []
    value.process = SimpleNamespace(stdin=SimpleNamespace(write=writes.append, flush=lambda: None))
    with pytest.raises(RuntimeError, match='check the task before retrying'):
        value.request('thread/start', {'ephemeral': False}, timeout=0.001)
    assert len(writes) == 1
    assert value._pending == {}
