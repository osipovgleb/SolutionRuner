"""Send a new turn through the desktop thread owner, without steering it.

The versioned local IPC framing and follower request are used by the installed
desktop app. Fail closed on incompatible versions; never replay a timed-out turn.
"""

import json
import os
from pathlib import Path
import socket
import stat
import struct
from uuid import uuid4


class OwnerUnavailable(RuntimeError):
    """No desktop client currently owns this thread."""


def send_owner_turn(thread_id: str, prompt: str, images: tuple[Path, ...] = (), *, socket_path: Path | None = None) -> None:
    path = socket_path or Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "ipc/ipc.sock"
    try:
        info = path.stat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            raise RuntimeError("Сокет Codex App не принадлежит текущему пользователю.")
    except FileNotFoundError as exc:
        raise OwnerUnavailable("Codex App не запущен.") from exc
    client_id = "initializing-client"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(20)
        try:
            connection.connect(str(path))

            def read_exact(length):
                result = bytearray()
                while len(result) < length:
                    part = connection.recv(length - len(result))
                    if not part:
                        raise RuntimeError("Соединение с Codex App закрыто. Проверьте чат перед повторной отправкой.")
                    result.extend(part)
                return result

            def request(method, params, version=1, target=None):
                request_id = str(uuid4())
                message = {"type": "request", "requestId": request_id,
                           "sourceClientId": client_id, "version": version,
                           "method": method, "params": params}
                if target:
                    message["targetClientId"] = target
                encoded = json.dumps(message).encode()
                connection.sendall(struct.pack("<I", len(encoded)) + encoded)
                while True:
                    size = struct.unpack("<I", read_exact(4))[0]
                    if not 0 < size <= 32 * 1024 * 1024:
                        raise RuntimeError("Codex App вернул несовместимый ответ.")
                    reply = json.loads(read_exact(size))
                    if reply.get("type") == "response" and reply.get("requestId") == request_id:
                        return reply

            initialized = request("initialize", {"clientType": "cli"})
            if initialized.get("resultType") != "success":
                raise RuntimeError("Codex App не принял подключение дэшборда.")
            client_id = initialized["result"]["clientId"]
            owner = request("thread-owner-discovery", {"hostId": "local", "conversationId": thread_id})
            if owner.get("resultType") != "success":
                if owner.get("error") == "no-client-found":
                    raise OwnerUnavailable("Откройте связанный чат в Codex App.")
                raise RuntimeError(f"Не удалось найти владельца чата: {owner.get('error')}")
            if not owner.get("result", {}).get("supportsUntrustedAppInput"):
                raise RuntimeError("Владелец чата использует несовместимую версию Codex App.")
            inputs = [{"type": "text", "text": prompt}]
            inputs.extend({"type": "localImage", "path": str(image.resolve())} for image in images)
            reply = request("thread-follower-start-turn", {
                "conversationId": thread_id,
                "turnStart": {"request": {"threadId": thread_id, "input": inputs}},
            }, version=2, target=owner["handledByClientId"])
            if reply.get("resultType") != "success":
                raise RuntimeError(f"Codex App не принял новое сообщение: {reply.get('error')}")
        except (OSError, ValueError, KeyError) as exc:
            raise RuntimeError(f"Сообщение не подтверждено Codex App: {exc}. Проверьте чат перед повтором.") from exc
