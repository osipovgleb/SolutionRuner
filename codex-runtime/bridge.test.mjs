import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createServer} from 'node:http';
import {mkdtemp, rm} from 'node:fs/promises';
import {createInterface} from 'node:readline';
import {once} from 'node:events';
import test from 'node:test';
import {WebSocketServer} from 'ws';

test('T3 bridge uses one shared connection, forwards errors and preserves the server on exit', {timeout: 5000}, async () => {
  const dir = await mkdtemp('/tmp/sr-codex-');
  const path = `${dir}/daemon.sock`;
  const server = createServer();
  const ws = new WebSocketServer({server});
  let connections = 0;
  const methods = [];
  ws.on('connection', (socket) => {
    connections++;
    socket.on('message', (raw) => {
      const request = JSON.parse(raw);
      methods.push(request.method);
      if (!('id' in request)) return;
      const send = (reply) => socket.send(JSON.stringify({id: request.id, ...reply}));
      if (request.method === 'initialize') send({result: {codexHome: '/shared/codex'}});
      else if (request.method === 'denied') send({error: {code: -1, message: 'native task locked'}});
      else if (request.method === 'turn/start') {
        socket.send(JSON.stringify({method: 'turn/completed', params: {
          threadId: 'same-task', turn: {id: 'fast-turn', status: 'completed', items: [{privateToolOutput: 'omit'}]},
        }}));
        send({result: {turn: {id: 'fast-turn', status: 'inProgress'}}});
      } else send({result: {thread: {id: 'same-task'}, params: request.params}});
    });
  });
  server.listen(path);
  await once(server, 'listening');
  const child = spawn(process.execPath, ['bridge.mjs', path], {cwd: import.meta.dirname});
  let diagnostics = '';
  child.stderr.on('data', (data) => { diagnostics += data.toString(); });
  const lines = createInterface({input: child.stdout});
  const iterator = lines[Symbol.asyncIterator]();
  const read = async () => {
    const line = await iterator.next();
    assert.equal(line.done, false, diagnostics || 'Bridge exited without a reply');
    return JSON.parse(line.value);
  };
  const send = (id, method, params = {}) => child.stdin.write(JSON.stringify({id, method, params}) + '\n');
  try {
    assert.deepEqual(await read(), {ready: true, codexHome: '/shared/codex'});
    send(10, 'thread/start', {ephemeral: false});
    assert.equal((await read()).result.thread.id, 'same-task');
    send(11, 'thread/name/set', {threadId: 'same-task'});
    assert.equal((await read()).result.params.threadId, 'same-task');
    send(12, 'turn/start', {threadId: 'same-task'});
    const notice = await read();
    assert.equal(notice.notification.params.turn.id, 'fast-turn');
    assert.equal('items' in notice.notification.params.turn, false);
    assert.equal((await read()).id, 12);
    send(13, 'denied');
    assert.match((await read()).error.message, /native task locked/);
    assert.equal(connections, 1);
    assert.deepEqual(methods.slice(0, 2), ['initialize', 'initialized']);
    for (const socket of ws.clients) socket.close();
    assert.match((await read()).fatal, /stream ended/);
    child.kill();
    await once(child, 'exit');
    assert.equal(server.listening, true);
  } finally {
    child.kill();
    lines.close();
    for (const socket of ws.clients) socket.terminate();
    ws.close();
    await new Promise((resolve) => server.close(resolve));
    await rm(dir, {recursive: true, force: true});
  }
});
