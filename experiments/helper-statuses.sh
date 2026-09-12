#!/usr/bin/env bash
# Read aggregated TeacherHelper Helpers statuses one source group at a time.
set -euo pipefail

input=${INPUT:-var/dashboard/work-group-uuids.json}
output=${OUTPUT:-var/dashboard/helper-statuses.jsonl}
pause_seconds=${PAUSE_SECONDS:-5}
mcp_url=${TEACHERHELPER_MCP_URL:-https://lessons-helper.ru/mcp}
curl_bin=${CURL_BIN:-curl}
sleep_bin=${SLEEP_BIN:-sleep}
api_key=${TEACHERHELPER_MCP_API_KEY:?Set TEACHERHELPER_MCP_API_KEY before running this script}

mkdir -p "$(dirname "$output")"
request_id=0
first=1

while IFS= read -r group; do
  if (( ! first )); then "$sleep_bin" "$pause_seconds"; fi
  first=0
  request_id=$((request_id + 1))
  group_key=$(jq -r '.group_key' <<<"$group")
  group_uuid=$(jq -r '.group_uuid' <<<"$group")
  request=$(jq -nc --arg id "$group_uuid" --argjson request_id "$request_id" '
    {jsonrpc:"2.0", id:$request_id, method:"tools/call",
     params:{name:"get_source_catalog_status_summary", arguments:{target_id:$id, target_type:"group"}}}')

  if response=$("$curl_bin" --fail --silent --show-error --max-time 60 "$mcp_url" \
      -H "Authorization: Bearer $api_key" \
      -H 'Content-Type: application/json' \
      -H 'Accept: application/json, text/event-stream' \
      -H 'MCP-Protocol-Version: 2025-06-18' \
      --data "$request"); then
    if helpers=$(jq -ce '.result.structuredContent.pipeline_stage_status_counts.helpers' <<<"$response"); then
      jq -nc --arg group_key "$group_key" --arg group_uuid "$group_uuid" --argjson helpers "$helpers" \
        '{group_key:$group_key, group_uuid:$group_uuid, helpers:$helpers}' >>"$output"
      continue
    fi
    error='MCP response has no Helpers status summary'
  else
    error='MCP request failed'
  fi
  jq -nc --arg group_key "$group_key" --arg group_uuid "$group_uuid" --arg error "$error" \
    '{group_key:$group_key, group_uuid:$group_uuid, error:$error}' >>"$output"
done < <(jq -c '.groups[] | {group_key, group_uuid}' "$input")
