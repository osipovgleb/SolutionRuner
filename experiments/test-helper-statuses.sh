#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/groups.json" <<'JSON'
{"groups":[{"group_key":"42","group_uuid":"group-uuid"}]}
JSON
cat >"$tmp/curl" <<'SH'
#!/usr/bin/env bash
printf '%s\n' '{"result":{"structuredContent":{"pipeline_stage_status_counts":{"helpers":{"ready":2,"pending":1}}}}}'
SH
cat >"$tmp/sleep" <<'SH'
#!/usr/bin/env bash
:
SH
chmod +x "$tmp/curl" "$tmp/sleep"

INPUT="$tmp/groups.json" OUTPUT="$tmp/statuses.jsonl" CURL_BIN="$tmp/curl" SLEEP_BIN="$tmp/sleep" \
  "$root/experiments/helper-statuses.sh"

jq -e '
  .group_key == "42"
  and .helpers.ready == 2
  and .helpers.pending == 1
' "$tmp/statuses.jsonl" >/dev/null
