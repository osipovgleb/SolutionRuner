import json
import socket
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

import pytest

from solution_runner.dashboard.codex_owner import send_owner_turn


@pytest.fixture
def ipc_path():
    with TemporaryDirectory(prefix='sr-ipc-', dir='/tmp') as directory:
        yield Path(directory) / 'ipc.sock'


@pytest.mark.parametrize('reject_turn', [False, True])
def test_owner_delivery_uses_new_turn_with_native_images_and_never_steers(tmp_path, reject_turn, ipc_path):
    path = ipc_path
    calls = []
    errors = []
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(str(path))
        listener.listen()
        def serve():
            try:
                with listener.accept()[0] as connection:
                    connection.settimeout(3)
                    def exact(n):
                        data = b''
                        while len(data) < n:
                            data += connection.recv(n-len(data))
                        return data
                    for index in range(3):
                        request = json.loads(exact(struct.unpack('<I', exact(4))[0]))
                        calls.append(request)
                        result = {'clientId': 'dashboard'} if index == 0 else {'supportsUntrustedAppInput': True} if index == 1 else {'result': {'turn': {'id': 'new-turn'}}}
                        reply = {'type': 'response', 'requestId': request['requestId'], 'resultType': 'error' if reject_turn and index == 2 else 'success', 'handledByClientId': 'desktop', 'result': result, 'error': 'turn already running'}
                        raw = json.dumps(reply).encode()
                        frame = struct.pack('<I', len(raw)) + raw
                        connection.sendall(frame[:2])
                        connection.sendall(frame[2:])
            except Exception as exc:
                errors.append(exc)
        thread = Thread(target=serve, daemon=True)
        thread.start()
        image = tmp_path / 'image with spaces.png'
        if reject_turn:
            with pytest.raises(RuntimeError, match='turn already running'):
                send_owner_turn('thread-1', 'Look', (image,), socket_path=path)
        else:
            send_owner_turn('thread-1', 'Look', (image,), socket_path=path)
        thread.join(4)
    assert not errors
    assert [call['method'] for call in calls] == ['initialize', 'thread-owner-discovery', 'thread-follower-start-turn']
    assert calls[-1]['version'] == 2
    assert calls[-1]['targetClientId'] == 'desktop'
    assert calls[-1]['params']['turnStart']['request']['input'] == [
        {'type': 'text', 'text': 'Look'}, {'type': 'localImage', 'path': str(image.resolve())},
    ]
