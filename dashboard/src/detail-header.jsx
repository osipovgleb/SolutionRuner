import { agentStatusLabels, Icon } from "./group-card.jsx";
import { RunStatus } from "./activity-tabs.jsx";
import { columns, teacherHelperGroupUrl } from "./model.js";

export function DetailHeader({ group, onClose, removeGroup, removing, openRegistration, archiveCodex, archivingCodex, restartAgent, restartingAgent, latestDryRun, latestApply }) {
  const teacherhelperUrl = teacherHelperGroupUrl(group.teacherhelper);
  const columnTitle = columns.find((column) => column.id === group.column)?.title || group.column;
  const agentStatus = agentStatusLabels[group.agent_status];
  return (
      <header class="detail-header">
        <div class="detail-heading">
          <div class="detail-kicker">
            {teacherhelperUrl
              ? <a class="detail-group-link" href={teacherhelperUrl} target="_blank" rel="noreferrer">Группа {group.id}</a>
              : <>Группа {group.id}</>
            } · {group.source}
          </div>
          <h2>{group.title}</h2>
          {group.path && group.path !== group.title && <p>{group.path}</p>}
          <div class="detail-run-status">
            <span>Этап: <b>{columnTitle}</b></span>
            <RunStatus label="Dry-run" run={latestDryRun} />
            <RunStatus label="Apply" run={latestApply} />
          </div>
          {agentStatus && <div class={`detail-agent-state agent-${group.agent_status || "idle"}`}>
            <span><b>Codex:</b> {agentStatus}</span>
            {group.agent_summary && <span>{group.agent_summary}</span>}
            {group.agent_status === "blocked" && group.codex_thread_id && <button class="secondary-button" onClick={restartAgent} disabled={restartingAgent}>{restartingAgent ? "Запускаю…" : "Перезапустить"}</button>}
          </div>}
        </div>
        <div class="detail-actions">
          <button class="secondary-button" onClick={removeGroup} disabled={removing}>{removing ? "Удаляю…" : "Удалить с доски"}</button>
          {group.task_url
            ? <a class="secondary-button codex-link" href={group.task_url}><Icon>↗</Icon>Codex</a>
            : <button class="secondary-button" onClick={openRegistration}><Icon>＋</Icon>Связать с Codex</button>
          }
          {group.column === "done" && group.codex_thread_id && <button class="secondary-button" onClick={archiveCodex} disabled={archivingCodex || group.codex_archived}>
            {group.codex_archived ? "Чат архивирован" : archivingCodex ? "Архивирую…" : "Архивировать чат"}
          </button>}
          <button class="icon-button" onClick={onClose} aria-label="Закрыть">×</button>
        </div>
      </header>
  );
}
