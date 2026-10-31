"""One T3 transport connection to the existing Codex daemon, never a private runtime."""

from __future__ import annotations

import atexit
import hashlib
import json
from pathlib import Path
from queue import Empty, Queue
import subprocess
from threading import Condition, Lock, Thread
from typing import Any


class SharedCodexClient:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._condition = Condition()
        self._write_lock = Lock()
        self._pending: dict[int, Queue] = {}
        self._sequence = 0
        self._ready: Queue = Queue()
        self._completed: dict[str, dict] = {}
        self._active: dict[str, str] = {}
        self._failure: str | None = None
        runtime = project_root / 'codex-runtime'
        node = subprocess.run(['node', '--version'], capture_output=True, text=True, check=True, timeout=10)
        version_parts = tuple(int(part) for part in node.stdout.strip().lstrip('v').split('.')[:2])
        if version_parts < (24, 10):
            raise RuntimeError('Shared Codex transport requires Node >=24.10')
        fingerprint = hashlib.sha256((runtime / 'package-lock.json').read_bytes()).hexdigest()
        marker = runtime / 'node_modules/.solution-runner-lock'
        if not marker.is_file() or marker.read_text() != fingerprint:
            logs = project_root / 'var/dashboard/logs'
            logs.mkdir(parents=True, exist_ok=True)
            with (logs / 'codex-transport-install.log').open('a') as output:
                subprocess.run(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'],
                               cwd=runtime, stdout=output, stderr=subprocess.STDOUT, check=True, timeout=120)
            marker.write_text(fingerprint)
        version = subprocess.run(
            ['codex', 'app-server', 'daemon', 'version'],
            capture_output=True, text=True, check=True, timeout=10,
        )
        daemon = json.loads(version.stdout)
        if daemon.get('status') != 'running':
            subprocess.run(['codex', 'app-server', 'daemon', 'start'],
                           capture_output=True, text=True, check=True, timeout=30)
            version = subprocess.run(['codex', 'app-server', 'daemon', 'version'],
                                     capture_output=True, text=True, check=True, timeout=10)
            daemon = json.loads(version.stdout)
        socket_path = daemon.get('socketPath')
        if not socket_path:
            raise RuntimeError('Codex shared daemon has no control socket')
        bridge = project_root / 'codex-runtime/bridge.mjs'
        logs = project_root / 'var/dashboard/logs'
        logs.mkdir(parents=True, exist_ok=True)
        with (logs / 'codex-shared-transport.log').open('a') as errors:
            self.process = subprocess.Popen(
                ['node', str(bridge), socket_path], cwd=project_root,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors,
                text=True, bufsize=1,
            )
        Thread(target=self._read, daemon=True, name='codex-shared-transport').start()
        try:
            ready = self._ready.get(timeout=15)
            if not ready.get('ready'):
                raise RuntimeError(ready.get('error', 'Codex shared transport failed'))
            self.codex_home = ready.get('codexHome')
        except (Empty, RuntimeError) as exc:
            self.close()
            raise RuntimeError(f'Cannot connect to shared Codex runtime: {exc}') from exc

    def _read(self) -> None:
        try:
            for line in self.process.stdout:
                message = json.loads(line)
                if message.get('ready'):
                    self._ready.put(message)
                elif message.get('fatal'):
                    raise RuntimeError(message['fatal'])
                elif 'id' in message:
                    with self._condition:
                        pending = self._pending.get(message['id'])
                    if pending is not None:
                        pending.put(message)
                elif message.get('notification', {}).get('method') == 'turn/completed':
                    params = message['notification']['params']
                    turn = params['turn']
                    with self._condition:
                        self._completed[turn['id']] = turn
                        if self._active.get(params['threadId']) == turn['id']:
                            self._active.pop(params['threadId'], None)
                        self._condition.notify_all()
            raise RuntimeError('Shared Codex transport disconnected; retry the operation')
        except Exception as exc:
            self._fail(str(exc))

    def _fail(self, message: str) -> None:
        with self._condition:
            self._failure = message
            for pending in self._pending.values():
                pending.put({'error': {'message': message}})
            self._condition.notify_all()
        self._ready.put({'error': message})

    def request(self, method: str, params: dict, timeout: float = 45) -> dict:
        pending: Queue = Queue()
        with self._condition:
            if self._failure:
                raise RuntimeError(self._failure)
            self._sequence += 1
            key = self._sequence
            self._pending[key] = pending
        try:
            with self._write_lock:
                self.process.stdin.write(json.dumps({'id': key, 'method': method, 'params': params}) + '\n')
                self.process.stdin.flush()
            reply = pending.get(timeout=timeout)
            if reply.get('error'):
                raise RuntimeError(f"Codex {method}: {reply['error']['message']}")
            return reply.get('result') or {}
        except Empty as exc:
            # Never replay a write automatically: it may have reached the daemon.
            raise RuntimeError(f'Codex {method} timed out; check the task before retrying') from exc
        except OSError as exc:
            raise RuntimeError(f'Codex {method}: shared transport disconnected') from exc
        finally:
            with self._condition:
                self._pending.pop(key, None)

    def start_turn(self, thread_id: str, prompt: str, model: str, effort: str) -> str:
        with self._condition:
            self._condition.wait_for(lambda: thread_id not in self._active or self._failure)
            if self._failure:
                raise RuntimeError(self._failure)
        result = self.request('turn/start', {
            'threadId': thread_id, 'model': model, 'effort': effort,
            'input': [{'type': 'text', 'text': prompt}],
        })
        turn = result.get('turn') or {}
        if not turn.get('id'):
            raise RuntimeError('Codex did not acknowledge the turn')
        with self._condition:
            if turn['id'] not in self._completed:
                self._active[thread_id] = turn['id']
        return turn['id']

    def wait_turn(self, turn_id: str) -> int:
        with self._condition:
            self._condition.wait_for(lambda: turn_id in self._completed or self._failure)
            if self._failure:
                raise RuntimeError(self._failure)
            turn = self._completed.pop(turn_id)
        return 0 if turn['status'] == 'completed' else 1

    def close(self) -> None:
        # Only disconnect this client; the daemon owns running tasks.
        if self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)


_clients: dict[Path, SharedCodexClient] = {}
_clients_lock = Lock()


def shared_client(project_root: Path) -> SharedCodexClient:
    root = project_root.resolve()
    with _clients_lock:
        client = _clients.get(root)
        if client is None or client._failure:
            if client is not None:
                client.close()
            try:
                client = SharedCodexClient(root)
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                raise RuntimeError(f'Cannot start shared Codex transport: {exc}') from exc
            _clients[root] = client
        return client


@atexit.register
def close_clients() -> None:
    for client in tuple(_clients.values()):
        client.close()
