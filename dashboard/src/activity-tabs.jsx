import { useEffect, useState } from "preact/hooks";
import { createApi } from "./api.js";
import { canApplyTask, formatTaskError } from "./model.js";

const api = createApi();
const runStageLabels = { solution: "Решение", apply: "Запись", helpers: "Helpers" };

function EmptyTab({ title, text }) {
  return <div class="empty-tab"><span class="empty-icon">≡</span><h3>{title}</h3><p>{text}</p></div>;
}

export function RunStatus({ label, run }) {
  return <div class="detail-run">
    <span>{label}: <b>{run ? runLabels[run.status] || run.status : "не запускался"}</b>{run && <time>{formatRunDate(run)}</time>}</span>
    {Object.entries(run?.stages || {}).map(([stage, counts]) => {
      const errors = counts.failed + counts.blocked + counts.skipped;
      return <span class={errors ? "run-stage-error" : ""} title={`Ошибки: ${counts.failed}; блокировки: ${counts.blocked}; пропуски: ${counts.skipped}`}>
        {runStageLabels[stage] || stage}: <b>{errors}</b>
      </span>;
    })}
  </div>;
}

const runLabels = {
  apply: "Запись",
  helpers: "Helpers",
  "dry-run": "Тестовый прогон",
  group: "Вся группа",
  problem: "Одна задача",
  completed: "Завершён",
  completed_with_errors: "Завершён с ошибками",
  failed: "Ошибка",
};

function runKindLabel(run) {
  if (run.kind === "helpers" && run.scope === "group") return "Helpers для всех";
  return runLabels[run.kind] || run.kind;
}

function formatRunDate(run) {
  if (!run?.started_at) return "Дата неизвестна";
  return new Date(run.started_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
}

export function RunTab({ activity }) {
  const run = activity?.latest;
  if (!run) return <EmptyTab title="Запусков нет" text="Для этой группы ещё нет сохранённых локальных отчётов." />;
  return <section class="activity-card">
    <div class="activity-heading"><div><span>Последний запуск</span><strong>{runKindLabel(run)}</strong></div><time>{formatRunDate(run)}</time></div>
    <dl class="activity-stats">
      <div><dt>Режим</dt><dd>{runLabels[run.scope] || run.scope}</dd></div>
      <div><dt>Статус</dt><dd>{runLabels[run.status] || run.status}</dd></div>
      <div><dt>Задач</dt><dd>{run.targets}</dd></div>
      <div><dt>Подготовлено</dt><dd>{run.prepared}</dd></div>
      <div><dt>Ошибок</dt><dd class={run.failed ? "activity-error" : ""}>{run.failed}</dd></div>
    </dl>
  </section>;
}

export function ProblemsTab({ activity, inventory, onOpenProblem, onApplyProblem, runningProblemId, applyingProblemId }) {
  const problems = activity?.problems || [];
  if (!problems.length) return <EmptyTab title="Неразобранных проблем нет" text="В актуальном индексе задач нет ошибок Apply или Helpers." />;
  return <section class="activity-section">
    <div class="activity-section-title"><strong>{problems.length} проблем</strong><span>Текущий незакрытый статус по задачам</span></div>
    <div class="inventory-table-wrap"><table class="inventory-table activity-table">
      <thead><tr><th>Задача</th><th>Apply</th><th>Helpers</th><th>Причина</th><th>Действия</th></tr></thead>
      <tbody>{problems.map((problem) => {
        const task = inventory?.tasks?.find((item) => item.problem_id === problem.problem_id);
        return <tr key={problem.problem_id}>
        <td><strong>Задача {problem.source_problem_id}</strong></td>
        <td>{problem.apply_status || "—"}</td><td>{problem.helpers_status || "—"}</td><td class="activity-reason">{formatTaskError(problem.error)}</td>
        <td><div class="task-actions">
          <button class="secondary-button" onClick={() => onOpenProblem(problem)}>Открыть проверку</button>
          <button class="primary-button" onClick={() => onApplyProblem(task)} disabled={!canApplyTask(task, Boolean(runningProblemId || applyingProblemId))}>
            {applyingProblemId === problem.problem_id ? "Применяю…" : "Повторить Apply"}
          </button>
        </div></td>
      </tr>;
      })}</tbody>
    </table></div>
  </section>;
}

function HistoryRow({ run }) {
  return <tr key={run.run_name}>
        <td>{formatRunDate(run)}</td><td>{runKindLabel(run)}</td><td>{runLabels[run.scope] || run.scope}</td>
        <td>{runLabels[run.status] || run.status}</td><td>{run.targets}</td><td class={run.failed ? "activity-error" : ""}>{run.failed}</td>
      </tr>;
}

export function HistoryTab({ activity }) {
  const runs = activity?.runs || [];
  if (!runs.length) return <EmptyTab title="История пуста" text="Сохранённых запусков для этой группы пока нет." />;
  return <section class="activity-section">
    <div class="activity-section-title"><strong>{runs.length} запусков</strong><span>Сначала новые</span></div>
    <div class="inventory-table-wrap"><table class="inventory-table activity-table">
      <thead><tr><th>Дата</th><th>Тип</th><th>Режим</th><th>Статус</th><th>Задач</th><th>Ошибки</th></tr></thead>
      <tbody>{runs.map((run) => <HistoryRow key={run.run_name} run={run} />)}</tbody>
    </table></div>
  </section>;
}

function useJobPolling(groupId, setJobs, setError) {
  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const payload = await api.listJobs(groupId);
        if (active) { setJobs(payload.jobs); setError(""); }
      } catch {
        if (active) setError("Не удалось загрузить очередь заданий.");
      }
    };
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => { active = false; clearInterval(timer); };
  }, [groupId]);
}

export function JobHistory({ groupId }) {
  const [jobs, setJobs] = useState([]);
  const [error, setError] = useState("");
  const [log, setLog] = useState(null);
  const [loadingLog, setLoadingLog] = useState(false);
  useJobPolling(groupId, setJobs, setError);
  const openLog = async (jobId) => {
    setLoadingLog(true);
    try {
      const payload = await api.getJobLog(jobId);
      setLog({ id: jobId, text: payload.log });
    } catch {
      setError("Не удалось загрузить лог задания.");
    } finally {
      setLoadingLog(false);
    }
  };
  const statuses = { queued: "В очереди", running: "Выполняется", completed: "Завершено", failed: "Ошибка", interrupted: "Прервано" };
  const kinds = { "dry-run": "Тестовый прогон", "apply-group": "Запись группы", "apply-problem": "Запись задачи", helpers: "Helpers" };
  return <section class="job-history">
    <h3>Задания</h3>
    {error && <p class="sample-error">{error}</p>}
    {!jobs.length && !error && <p>Заданий пока нет.</p>}
    {jobs.map((job) => <div class="job-history-row" key={job.id}>
      <span>#{job.id} · {kinds[job.kind] || job.kind} · {statuses[job.status] || job.status}</span>
      <small>{new Date(job.created_at).toLocaleString("ru")}</small>
      {job.error && <p class="sample-error">{job.error}</p>}
      {job.status === "interrupted" && <p>Перед повтором проверьте результат записи в TeacherHelper.</p>}
      <button class="secondary-button" onClick={() => openLog(job.id)} disabled={loadingLog}>Лог</button>
    </div>)}
    {log && <div><h4>Лог задания #{log.id}</h4><pre class="job-log">{log.text || "Вывод пока отсутствует."}</pre></div>}
  </section>;
}

