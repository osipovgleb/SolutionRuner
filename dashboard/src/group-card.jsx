import { compactCatalogLabel, teacherHelperGroupUrl } from "./model.js";

export const agentStatusLabels = {
  working: "Агент работает",
  verifying: "Идёт полный dry-run",
  updated: "Есть обновление",
  no_changes: "Проверено без изменений",
  needs_input: "Нужен ответ",
  blocked: "Агент заблокирован",
  delivery_failed: "Сообщение не доставлено",
};
const jobKindLabels = { dry_run: "Dry-run", apply: "Apply", helpers: "Helpers" };
const jobStatusLabels = { queued: "ожидает", running: "выполняется", retry_wait: "ожидает повтора" };

export const Icon = ({ children }) => <span class="icon" aria-hidden="true">{children}</span>;

export function GroupCard({ group, onOpen, onDragStart }) {
  const { transformed, total, helpers, errors } = group.stats;
  const teacherhelperUrl = teacherHelperGroupUrl(group.teacherhelper);
  const agentStatus = agentStatusLabels[group.agent_status];
  return (
    <div
      class={`group-card-shell${teacherhelperUrl ? " has-group-link" : ""}`}
      draggable={group.column !== "jobs"}
      onDragStart={(event) => onDragStart(event, group.id)}
    >
      <button
        class="group-card"
        onClick={() => onOpen(group.id)}
      >
        <div class="card-topline">
          <span class="group-id">Группа {group.id}</span>
          <span class="source-pill">{compactCatalogLabel(group.source)}</span>
        </div>
        {group.revision_requested && <span class="agent-waiting">Ждёт агента</span>}
        {group.job && <span class={`job-status job-${group.job.status}`}>
          {jobKindLabels[group.job.kind] || group.job.kind}: {jobStatusLabels[group.job.status] || group.job.status}
        </span>}
        {agentStatus && <span class={`agent-status agent-${group.agent_status}`} title={group.agent_summary || ""}>{agentStatus}</span>}
        {group.agent_status === "needs_input" && group.agent_summary && <span class="agent-question">{group.agent_summary}</span>}
        <strong>{group.title}</strong>
        {group.path && group.path !== group.title && <span class="group-path">{group.path}</span>}
        <div class="progress-track"><span style={{ width: `${total ? Math.round((transformed / total) * 100) : 0}%` }} /></div>
        <div class="card-metrics">
          <span title="Обработано"><Icon>✓</Icon>{transformed}/{total}</span>
          <span title="Helpers ready"><Icon>H</Icon>{helpers}</span>
          {errors > 0 && <span class="metric-error" title="Ошибки"><Icon>!</Icon>{errors}</span>}
          <span class={group.task ? "task-linked" : "task-missing"}>{group.task ? "Codex связан" : "Нет задачи"}</span>
        </div>
      </button>
      {teacherhelperUrl && <a class="group-id-link" href={teacherhelperUrl} target="_blank" rel="noreferrer">Группа {group.id}</a>}
    </div>
  );
}

