/** T3 Code's correlated JSON-RPC transport, connected to the shared Codex daemon. */
import * as Deferred from 'effect/Deferred';
import * as Effect from 'effect/Effect';
import * as Queue from 'effect/Queue';
import * as Sink from 'effect/Sink';
import * as Stdio from 'effect/Stdio';
import * as Stream from 'effect/Stream';
import { createInterface } from 'node:readline';
import WebSocket from 'ws';
import { makeCodexAppServerPatchedProtocol } from './vendor/effect-codex-app-server/protocol.ts';
import { CodexAppServerRequestError, CodexAppServerInputStreamEndedError } from './vendor/effect-codex-app-server/errors.ts';

const emit = (value) => process.stdout.write(JSON.stringify(value) + '\n');

export const connect = (socketPath) => Effect.gen(function* () {
  const input = yield* Queue.unbounded();
  const closed = yield* Deferred.make();
  const socket = yield* Effect.acquireRelease(
    Effect.tryPromise(() => new Promise((resolve, reject) => {
      const ws = new WebSocket(`ws+unix://${socketPath}:/`);
      ws.on('message', (data) => Effect.runFork(Queue.offer(input, new TextEncoder().encode(data.toString() + '\n'))));
      ws.once('open', () => resolve(ws));
      ws.on('error', reject);
      ws.once('close', () => Effect.runFork(Effect.gen(function* () {
        yield* Deferred.succeed(closed, new CodexAppServerInputStreamEndedError({}));
        yield* Queue.end(input);
      })));
    })),
    (ws) => Effect.sync(() => ws.close()),
  );
  const stdio = Stdio.make({
    args: Effect.succeed([]),
    stdin: Stream.fromQueue(input),
    stdout: () => Sink.forEach((chunk) => Effect.tryPromise(() => new Promise((resolve, reject) => {
      socket.send(typeof chunk === 'string' ? chunk.trimEnd() : new TextDecoder().decode(chunk).trimEnd(),
        (error) => error ? reject(error) : resolve());
    }))),
    stderr: () => Sink.drain,
  });
  return yield* makeCodexAppServerPatchedProtocol({
    stdio,
    terminationError: Deferred.await(closed),
    onTermination: (error) => Effect.sync(() => emit({fatal: String(error.message ?? error)})),
    onRequest: (request) => Effect.fail(CodexAppServerRequestError.methodNotFound(request.method)),
    onNotification: (notification) => Effect.sync(() => {
      // Only lifecycle events cross into Python; tool payloads and tokens stay out of logs.
      if (notification.method === 'turn/completed') {
        const {threadId, turn} = notification.params;
        emit({notification: {method: notification.method, params: {
          threadId, turn: {id: turn.id, status: turn.status, error: turn.error},
        }}});
      }
    }),
  });
});

const main = Effect.gen(function* () {
  const protocol = yield* connect(process.argv[2]);
  const initialized = yield* protocol.request('initialize', {
    clientInfo: {name: 'solution-runner-dashboard', title: 'SolutionRunner', version: '2.0'},
    capabilities: {experimentalApi: true},
  });
  yield* protocol.notify('initialized');
  emit({ready: true, codexHome: initialized.codexHome});
  const lines = createInterface({input: process.stdin});
  yield* Stream.fromAsyncIterable(lines, (cause) => cause).pipe(Stream.runForEach((line) => Effect.gen(function* () {
    const request = JSON.parse(line);
    const outcome = yield* Effect.result(protocol.request(request.method, request.params));
    if (outcome._tag === 'Success') emit({id: request.id, result: outcome.success});
    else emit({id: request.id, error: {method: request.method, message: String(outcome.failure.message ?? outcome.failure)}});
  })));
});

if (process.argv[1]?.endsWith('/bridge.mjs')) {
  Effect.runPromise(main.pipe(Effect.scoped)).catch((error) => {
    emit({fatal: String(error.message ?? error)});
    process.exitCode = 1;
  });
}
