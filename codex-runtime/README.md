# Shared Codex transport

This adapter reuses the actual T3 Code JSON-RPC transport from revision
`e85539ab59f13bafd156f831d2e6690df67eb677`, copied unchanged from the existing
TeacherHelper adapter. `vendor/LICENSE` retains its MIT attribution.
Unlike TeacherHelper's ephemeral worker, it connects to the existing Codex
daemon's Unix WebSocket and creates persistent native threads.

Run `npm ci --ignore-scripts` here with Node >=24.10. Python starts one bridge
per dashboard project, correlates responses, and observes turn completion.
Closing the bridge disconnects the client, not the daemon or its tasks. Lost
mutating replies are never replayed automatically. Native errors reach the UI.
No credential values or tool-result payloads are written to the bridge log.

`npm test` runs the real vendored transport against a local fake daemon,
including errors and a completion notification preceding the start reply.
