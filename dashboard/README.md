# Group dashboard

Local Preact dashboard based on the lightweight board interaction model of
[OpenKanban](https://github.com/clawnify/OpenKanban). A small Python API reads
registered groups and local run reports, while SQLite stores board columns,
task links, comments, and the initialized task index.

New groups move through `Инициализация` first. The backend reads their IDs,
section flags, and image metadata through MCP once and stores no problem HTML.
Dashboard dry-runs use that SQLite index through the one common launcher and
never add `--apply`; real writes remain a separate, explicit step.

Dry-runs automatically initialize missing, partial, failed or outdated local
indexes before selecting a task or invoking the launcher. Existing initialization
jobs are awaited rather than duplicated, and a matching ready index is reused.
This covers registered groups arriving through Git without copying another
machine's SQLite database. Initialization errors stop the dry-run before launch.

After initialization, registration can reuse an existing Codex task for this
repository or create a new `gpt-6.1-sol` task with medium reasoning. A clean
full-group dry-run moves the card to review and enables Apply; a failed one moves
it to problems. Review/problem comments are forwarded to the linked Codex task
and invalidate the previous full-group approval.

Codex tasks use the host's shared Codex daemon and its `CODEX_HOME`. The
vendored T3 Code transport in `codex-runtime/` connects over its Unix WebSocket;
it does not start a private app-server per request. Node >=24.10 is required.
Locked transport dependencies are installed automatically with `npm ci
--ignore-scripts` on first use or when the lockfile changes. The shared daemon
is started if needed, and client disconnects do not terminate its tasks.

For simultaneous access from the local Codex desktop app and this dashboard,
the desktop app must also connect to that daemon. Using the same `CODEX_HOME`
with separate app-server processes still produces `already has an active
writer` / `This is open in another app`.

The installed macOS desktop build supports this opt-in connection mode:

```bash
codex app-server daemon start
launchctl setenv CODEX_APP_SERVER_USE_LOCAL_DAEMON 1
```

Then fully quit and reopen the desktop app after its active work finishes.
`launchctl setenv` applies to subsequently launched GUI processes in the current
login session; it does not change an already running app or survive logout.
The app must have no forced CLI/runtime override (`CODEX_APP_SERVER_FORCE_CLI`,
`CODEX_CLI_PATH`, or a configured custom CLI command). The mode is an internal
switch verified in the installed desktop build, not a portable public setting.
SSH is not required. To undo the opt-in, run
`launchctl unsetenv CODEX_APP_SERVER_USE_LOCAL_DAEMON` and restart the app.

Each card retains the native persistent `thread_id`; retries and comments reuse
that task. Continuations use the desktop IPC `thread-follower-start-turn` request to deliver a new turn to the existing owner,
including Codex App, instead of trying to acquire another writer with
`thread/resume`. HTTP success is returned only after the owner accepts the new turn. Delivery
errors are separate from agent failures, remain visible, and do not record an
undelivered comment as sent. A created ID is saved before admitting the first turn, including when
admission fails, and native errors are returned to the UI. Creation/name/start
share one runtime connection. Completion notifications update the linked card.
The host running the dashboard owns the task; local and remote hosts are never
silently mixed. T3 Code has a separate sidebar index: its native-session import
must point at the same host and Codex home; the transport does not replicate
T3's project database or synchronize tasks to other machines.

```bash
npm install
npm run build
cd ..
.venv/bin/python -m solution_runner.dashboard.server
```

The built dashboard is then available at `http://127.0.0.1:8765`.

## Persistent runner queue

The server stores dry-run, Apply and Helpers jobs in `dashboard_jobs` in the
same SQLite database as the board. One process owns the queue, protected by a
local file lock; jobs execute serially. Pending jobs resume in submission order
on restart. Jobs which were running become `interrupted` and are **not replayed**:
inspect the TeacherHelper result before submitting a replacement. Pending Apply
jobs re-check dry-run approval immediately before execution.

On graceful shutdown the current job finishes and pending jobs remain in the
DB for the next start. Without MCP credentials pending jobs are retained until
a configured restart. Initialization and Codex development tasks are outside
this runner queue. A forcibly killed server can leave a launcher or agent
process alive: check those processes and external results before retrying.

The History tab shows the last 100 jobs for the selected group and their logs.
API endpoints (same authentication as the board):

- `GET /api/jobs`: latest 100 jobs; optional `?group=GROUP_ID` filter.
- `GET /api/jobs/JOB_ID/log`: last 64 KiB of combined launcher stdout/stderr.

Launcher logs are kept in `var/dashboard/logs/job-JOB_ID.log`; Codex execution,
queue and app-server diagnostics are kept alongside them. Logs are local
artifacts, excluded from Git. Include the SQLite DB and `var/` artifacts in
backups; use SQLite's backup API for a live DB. Log rotation and scheduled
backups are not configured by this change.

## Access from other devices

Set credentials in the service environment, never in tracked files:

- `SOLUTION_RUNNER_DASHBOARD_PASSWORD`: browser login password (HTTP Basic).
- `SOLUTION_RUNNER_DASHBOARD_USER`: login name, default `owner`.
- `SOLUTION_RUNNER_DASHBOARD_TOKEN`: optional independent Bearer token for API clients.
- `SOLUTION_RUNNER_CODEX_MODEL` and `SOLUTION_RUNNER_CODEX_EFFORT`: optional
  overrides for newly created agent tasks; defaults remain unchanged.

Local loopback access remains available without credentials. Binding to another
interface requires a password or token. Configure the password even when a
reverse proxy connects to loopback. For browser use, set the password; a Bearer
only configuration is intended for API clients.
The existing Compose configuration passes these credentials from the host
environment; its non-loopback server also refuses to start without them.

For `https://lessons-helper.online`, the intended setup is an HTTPS reverse
proxy forwarding the frontend and `/api/` to the same dashboard instance. Keep
the Python server on loopback, preserve the original `Host` header, and use
HTTPS for remote credentials. Requests with a foreign Origin cannot mutate the
board. With authentication enabled, the local Vite cross-origin development
exception is disabled; use the built frontend on the server's own origin.

This repository checkout is development-only according to AGENTS.md. This
change prepares the application but does not deploy it, configure the domain,
install a service, or change machine policy. Service hosting must be arranged
on an authorized machine. All devices use HTTP API; do not share the SQLite
file over a network filesystem.

Comments for groups and individual problems accept up to four PNG, JPEG, GIF,
or WebP images (5 MiB each), by dropping files, pasting, or selecting files.
The composer previews attachments and retains them if delivery fails. Images
are stored under `var/dashboard/comment-images`, referenced from SQLite comment
history, and passed to the desktop owner as native `localImage` inputs. The CLI queue is not used: it steers active turns and rejects image attachments.
The task inventory refreshes every three seconds while its tab is open, including
updates made by an agent or another dashboard tab.
