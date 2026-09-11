import { render } from "preact";
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import katex from "katex";
import "katex/dist/katex.min.css";
import { createApi } from "./api.js";
import { canApplyGroup, canApplyTask, columns, compactCatalogLabel, filterGroups, formatTaskError, isTaskRecorded, teacherHelperGroupUrl } from "./model.js";
import "./styles.css";

const api = createApi();

const Icon = ({ children }) => <span class="icon" aria-hidden="true">{children}</span>;

function GroupCard({ group, onOpen, onDragStart }) {
  const { transformed, total, helpers, errors } = group.stats;
  const teacherhelperUrl = teacherHelperGroupUrl(group.teacherhelper);
  return (
    <div class={`group-card-shell${teacherhelperUrl ? " has-group-link" : ""}`}>
      <button
        class="group-card"
        onClick={() => onOpen(group.id)}
        draggable
        onDragStart={(event) => onDragStart(event, group.id)}
      >
        <div class="card-topline">
          <span class="group-id">Группа {group.id}</span>
          <span class="source-pill">{compactCatalogLabel(group.source)}</span>
        </div>
        {group.revision_requested && <span class="agent-waiting">Ждёт агента</span>}
        <strong>{group.title}</strong>
        <span class="group-path">{group.path}</span>
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

function HtmlSection({ html }) {
  const element = useRef(null);
  useEffect(() => {
    element.current?.querySelectorAll("[data-inline-latex]").forEach((node) => {
      katex.render(node.dataset.inlineLatex || "", node, {
        throwOnError: false,
        displayMode: node.dataset.formulaRenderMode === "display",
      });
    });
  }, [html]);
  return <div ref={element} class="teacher-content" dangerouslySetInnerHTML={{ __html: html || "" }} />;
}

function ProblemPreview({ card }) {
  return (
    <article class="problem-preview">
      <HtmlSection html={card.condition_html} />
      {card.solution_html && <><div class="solution-label">Решение</div><HtmlSection html={card.solution_html} /></>}
      {card.answer_html && <div class="preview-answer"><strong>Ответ:</strong><HtmlSection html={card.answer_html} /></div>}
    </article>
  );
}

function TaskInventory({ inventory, onOpenPreview, onRunProblem, onApplyProblem, onRejectProblem, runningProblemId, applyingProblemId, rejectingProblemId }) {
  const [filter, setFilter] = useState("all");
  if (!inventory) return <div class="preview-state">Состав группы ещё не инициализирован.</div>;
  const visible = inventory.tasks.filter((task) => {
    if (filter === "errors") return Boolean(task.error);
    if (filter === "ready") return [task.dry_run_status, task.apply_status, task.helpers_status].includes("ready") || task.helpers_status === "applied";
    if (filter === "skipped") return [task.dry_run_status, task.apply_status, task.helpers_status].includes("skipped");
    return true;
  });
  return <section class="task-inventory">
    <div class="inventory-toolbar">
      <strong>{inventory.tasks.length} задач</strong>
      <div>{[["all", "Все"], ["ready", "Готовы"], ["skipped", "Пропущены"], ["errors", "Ошибки"]].map(([id, label]) =>
        <button class={filter === id ? "active" : ""} onClick={() => setFilter(id)}>{label}</button>
      )}</div>
    </div>
    <div class="inventory-table-wrap"><table class="inventory-table">
      <thead><tr><th>Задача</th><th>Разделы</th><th>Картинки условия</th><th>Картинки решения</th><th>Dry-run</th><th>Apply</th><th>Helpers</th><th>Причина</th><th>Действия</th></tr></thead>
      <tbody>{visible.map((task) => {
        const conditionAssets = task.assets.filter((asset) => asset.section === "condition");
        const solutionAssets = task.assets.filter((asset) => asset.section === "solution");
        const recorded = isTaskRecorded(task);
        return <tr onClick={() => onOpenPreview(task)} class={task.problem_id === inventory.parent_problem_id ? "parent-task" : ""}>
          <td><button>Задача {task.source_problem_id}</button>{task.problem_id === inventory.parent_problem_id && <small>родитель</small>}</td>
          <td>{task.has_condition ? "У" : "—"} · {task.has_solution ? "Р" : "—"} · {task.has_answer ? "О" : "—"}</td>
          <td>{conditionAssets.map((asset) => asset.content_type.replace("image/", "")).join(", ") || "—"}</td>
          <td>{solutionAssets.map((asset) => asset.content_type.replace("image/", "")).join(", ") || "—"}</td>
          <td>{task.dry_run_status || "—"}</td><td>{task.apply_status || "—"}</td><td>{task.helpers_status || "—"}</td><td>{formatTaskError(task.error)}</td>
          <td><div class="task-actions">
            <button class="secondary-button" onClick={(event) => { event.stopPropagation(); onRunProblem(task); }} disabled={Boolean(runningProblemId || applyingProblemId)}>
              {runningProblemId === task.problem_id ? "Проверяю…" : "Проверить"}
            </button>
            <button class="primary-button" onClick={(event) => { event.stopPropagation(); onApplyProblem(task); }} disabled={!canApplyTask(task, Boolean(runningProblemId || applyingProblemId))}>
              {applyingProblemId === task.problem_id ? "Записываю…" : recorded ? "Записано" : "Записать"}
            </button>
            <button class="danger-button" title={task.problem_id === inventory.parent_problem_id ? "Родитель отклоняется только вместе с группой" : ""} onClick={(event) => { event.stopPropagation(); onRejectProblem(task); }} disabled={task.problem_id === inventory.parent_problem_id || Boolean(runningProblemId || applyingProblemId || rejectingProblemId)}>
              {rejectingProblemId === task.problem_id ? "Отклоняю…" : "Reject"}
            </button>
          </div></td>
        </tr>;
      })}</tbody>
    </table></div>
  </section>;
}

const runLabels = {
  apply: "Запись",
  "dry-run": "Тестовый прогон",
  group: "Вся группа",
  problem: "Одна задача",
  completed: "Завершён",
  completed_with_errors: "Завершён с ошибками",
  failed: "Ошибка",
};

function formatRunDate(run) {
  if (!run?.started_at) return "Дата неизвестна";
  return new Date(run.started_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
}

function RunTab({ activity }) {
  const run = activity?.latest;
  if (!run) return <EmptyTab title="Запусков нет" text="Для этой группы ещё нет сохранённых локальных отчётов." />;
  return <section class="activity-card">
    <div class="activity-heading"><div><span>Последний запуск</span><strong>{runLabels[run.kind] || run.kind}</strong></div><time>{formatRunDate(run)}</time></div>
    <dl class="activity-stats">
      <div><dt>Режим</dt><dd>{runLabels[run.scope] || run.scope}</dd></div>
      <div><dt>Статус</dt><dd>{runLabels[run.status] || run.status}</dd></div>
      <div><dt>Задач</dt><dd>{run.targets}</dd></div>
      <div><dt>Подготовлено</dt><dd>{run.prepared}</dd></div>
      <div><dt>Ошибок</dt><dd class={run.failed ? "activity-error" : ""}>{run.failed}</dd></div>
    </dl>
  </section>;
}

function ProblemsTab({ activity, inventory, onOpenProblem, onApplyProblem, runningProblemId, applyingProblemId }) {
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
            {applyingProblemId === problem.problem_id ? "Записываю…" : "Повторить запись"}
          </button>
        </div></td>
      </tr>;
      })}</tbody>
    </table></div>
  </section>;
}

function HistoryTab({ activity }) {
  const runs = activity?.runs || [];
  if (!runs.length) return <EmptyTab title="История пуста" text="Сохранённых запусков для этой группы пока нет." />;
  return <section class="activity-section">
    <div class="activity-section-title"><strong>{runs.length} запусков</strong><span>Сначала новые</span></div>
    <div class="inventory-table-wrap"><table class="inventory-table activity-table">
      <thead><tr><th>Дата</th><th>Тип</th><th>Режим</th><th>Статус</th><th>Задач</th><th>Ошибки</th></tr></thead>
      <tbody>{runs.map((run) => <tr key={run.run_name}>
        <td>{formatRunDate(run)}</td><td>{runLabels[run.kind] || run.kind}</td><td>{runLabels[run.scope] || run.scope}</td>
        <td>{runLabels[run.status] || run.status}</td><td>{run.targets}</td><td class={run.failed ? "activity-error" : ""}>{run.failed}</td>
      </tr>)}</tbody>
    </table></div>
  </section>;
}

function DetailPanel({ group, onClose, onGroupUpdate }) {
  const teacherhelperUrl = teacherHelperGroupUrl(group.teacherhelper);
  const [tab, setTab] = useState("preview");
  const [comment, setComment] = useState("");
  const [comments, setComments] = useState([]);
  const [editingTask, setEditingTask] = useState(false);
  const [codexTasks, setCodexTasks] = useState([]);
  const [selectedThreadId, setSelectedThreadId] = useState("");
  const [registering, setRegistering] = useState(false);
  const [taskError, setTaskError] = useState("");
  const [preview, setPreview] = useState(null);
  const [previewState, setPreviewState] = useState("loading");
  const [sampleIndex, setSampleIndex] = useState(0);
  const [addingSample, setAddingSample] = useState(false);
  const [sampleError, setSampleError] = useState("");
  const [dryRunMode, setDryRunMode] = useState("random");
  const [dryRun, setDryRun] = useState(null);
  const [runError, setRunError] = useState("");
  const [runningProblemId, setRunningProblemId] = useState(null);
  const [applyRun, setApplyRun] = useState(null);
  const [applyingProblemId, setApplyingProblemId] = useState(null);
  const [rejectingProblemId, setRejectingProblemId] = useState(null);
  const [initialization, setInitialization] = useState(null);
  const [inventory, setInventory] = useState(null);
  const [activity, setActivity] = useState(null);
  const refreshActivity = () => api.getActivity(group.id).then(setActivity).catch(() => setActivity(null));
  const loadPreview = (selectLast = false) => {
    setPreview(null);
    setPreviewState("loading");
    if (!selectLast) setSampleIndex(0);
    setSampleError("");
    return api.getPreview(group.id)
      .then((payload) => {
        setPreview(payload);
        setPreviewState("ready");
        if (selectLast) setSampleIndex(Math.max(payload.samples.length - 1, 0));
        return payload;
      })
      .catch(() => setPreviewState("missing"));
  };
  useEffect(() => {
    api.listComments(group.id)
      .then(({ comments: items }) => setComments(items))
      .catch(() => setComments([]));
  }, [group.id]);
  useEffect(() => {
    loadPreview();
    setDryRun(null);
    setRunningProblemId(null);
    setApplyRun(null);
    setApplyingProblemId(null);
    setRejectingProblemId(null);
    setRunError("");
    api.getDryRun(group.id).then(setDryRun).catch(() => setDryRun(null));
    api.getInitialization(group.id).then(setInitialization).catch(() => setInitialization(null));
    api.getTasks(group.id).then(setInventory).catch(() => setInventory(null));
    refreshActivity();
  }, [group.id]);
  useEffect(() => {
    if (!dryRun || !["queued", "running"].includes(dryRun.status)) return undefined;
    const timer = setInterval(async () => {
      try {
        const state = await api.getDryRun(group.id);
        setDryRun(state);
        if (!["queued", "running"].includes(state.status)) {
          const payload = await loadPreview(Boolean(state.append));
          if (runningProblemId && payload?.samples) {
            const index = payload.samples.findIndex((sample) => sample.problem_id === runningProblemId);
            if (index >= 0) {
              setSampleIndex(index);
              setTab("preview");
            }
          }
          setRunningProblemId(null);
          setAddingSample(false);
          api.getTasks(group.id).then(setInventory).catch(() => {});
          refreshActivity();
          const updated = await api.getGroup(group.id);
          onGroupUpdate(updated);
        }
      } catch {
        setRunError("Не удалось получить состояние тестового прогона.");
      }
    }, 1500);
    return () => clearInterval(timer);
  }, [group.id, dryRun?.status, runningProblemId]);
  useEffect(() => {
    if (!applyRun || !["queued", "running"].includes(applyRun.status)) return undefined;
    const timer = setInterval(async () => {
      try {
        const state = await api.getApply(group.id);
        setApplyRun(state);
        if (!["queued", "running"].includes(state.status)) {
          setApplyingProblemId(null);
          if (state.status === "failed") {
            setRunError(state.scope === "group" ? "Не все задачи группы удалось записать. Подробности — во вкладке «Проблемы»." : "Не удалось записать выбранную задачу.");
          }
          api.getTasks(group.id).then(setInventory).catch(() => {});
          refreshActivity();
          const updated = await api.getGroup(group.id);
          onGroupUpdate(updated);
        }
      } catch {
        setRunError("Не удалось получить состояние записи задачи.");
      }
    }, 1500);
    return () => clearInterval(timer);
  }, [group.id, applyRun?.status]);
  const startDryRun = async () => {
    setRunError("");
    try {
      setDryRun(await api.startDryRun(group.id, dryRunMode));
    } catch {
      setRunError("Не удалось запустить локальный тестовый прогон.");
    }
  };
  const addSample = async () => {
    setAddingSample(true);
    setSampleError("");
    try {
      setDryRun(await api.addPreviewSample(group.id));
    } catch {
      setSampleError("Не удалось добавить следующую задачу для проверки.");
      setAddingSample(false);
    }
  };
  const runProblem = async (task) => {
    setRunError("");
    setRunningProblemId(task.problem_id);
    try {
      setDryRun(await api.startProblemDryRun(group.id, task.problem_id));
    } catch {
      setRunningProblemId(null);
      setRunError("Не удалось проверить выбранную задачу.");
    }
  };
  const applyProblem = async (task) => {
    if (!window.confirm(`Записать изменения только для задачи ${task.source_problem_id}?`)) return;
    setRunError("");
    setApplyingProblemId(task.problem_id);
    try {
      setApplyRun(await api.applyProblem(group.id, task.problem_id));
    } catch {
      setApplyingProblemId(null);
      setRunError("Не удалось запустить запись выбранной задачи.");
    }
  };
  const applyGroup = async () => {
    if (!window.confirm(`Одобрить результат и записать все задачи группы «${group.title}» через MCP?`)) return;
    setRunError("");
    try {
      setApplyRun(await api.applyGroup(group.id));
    } catch {
      setRunError("Не удалось запустить запись всей группы. Сначала нужен успешный тестовый прогон.");
    }
  };
  const rejectProblem = async (task) => {
    const reason = window.prompt(`Почему задача ${task.source_problem_id} должна быть отклонена?`);
    if (!reason?.trim()) return;
    if (!window.confirm(`Отклонить задачу ${task.source_problem_id} через MCP? После этого она исчезнет из дальнейшей обработки.`)) return;
    setRunError("");
    setRejectingProblemId(task.problem_id);
    try {
      const result = await api.rejectProblem(group.id, task.problem_id, reason.trim());
      setInventory(await api.getTasks(group.id));
      await loadPreview();
      await refreshActivity();
      onGroupUpdate(result.group);
      setTab("tasks");
    } catch {
      setRunError("MCP не подтвердил отклонение задачи. Локальный индекс не изменён.");
    } finally {
      setRejectingProblemId(null);
    }
  };
  const selectedSample = preview?.samples?.[sampleIndex];
  const addComment = async () => {
    if (!comment.trim()) return;
    setRunError("");
    try {
      const result = await api.addComment(group.id, comment.trim());
      setComments([...comments, result.comment]);
      onGroupUpdate(result.group);
      setComment("");
    } catch {
      setRunError(group.codex_thread_id
        ? "Не удалось отправить комментарий в связанную Codex-задачу."
        : "Сначала свяжи группу с Codex-задачей.");
    }
  };
  const openRegistration = async () => {
    setEditingTask(true);
    setTaskError("");
    try {
      const result = await api.listCodexTasks();
      setCodexTasks(result.tasks || []);
    } catch {
      setTaskError("Не удалось получить список Codex-задач.");
    }
  };
  const registerGroup = async () => {
    setRegistering(true);
    setTaskError("");
    try {
      const result = await api.registerGroup(group.id, selectedThreadId || null);
      onGroupUpdate(result.group);
      setEditingTask(false);
    } catch {
      setTaskError("Не удалось зарегистрировать группу или создать Codex-задачу.");
    } finally {
      setRegistering(false);
    }
  };
  const retryInitialization = async () => {
    setInitialization(await api.startInitialization(group.id));
  };
  const openTaskPreview = (task) => {
    const index = preview?.samples?.findIndex((sample) => sample.problem_id === task.problem_id || sample.source_problem_id === task.source_problem_id) ?? -1;
    if (index >= 0) {
      setSampleIndex(index);
      setTab("preview");
    }
  };
  const openProblemPreview = async (problem) => {
    setRunError("");
    try {
      const payload = await api.getProblemPreview(group.id, problem.problem_id);
      setPreview(payload);
      setSampleIndex(0);
      setPreviewState("ready");
      setTab("preview");
    } catch {
      setRunError("Не удалось открыть normalized-контент этой задачи.");
    }
  };
  const selectedTask = inventory?.tasks?.find((task) => task.problem_id === selectedSample?.problem_id);
  const groupApplyActive = applyRun?.scope === "group" && ["queued", "running"].includes(applyRun.status);
  const groupBusy = groupApplyActive || ["queued", "running"].includes(dryRun?.status);

  return (
    <aside class="detail-panel">
      <header class="detail-header">
        <div>
          <div class="detail-kicker">
            {teacherhelperUrl
              ? <a class="detail-group-link" href={teacherhelperUrl} target="_blank" rel="noreferrer">Группа {group.id}</a>
              : <>Группа {group.id}</>
            } · {group.source}
          </div>
          <h2>{group.title}</h2>
          <p>{group.path}</p>
        </div>
        <button class="icon-button" onClick={onClose} aria-label="Закрыть">×</button>
      </header>

      <div class="status-strip">
        <span><i class="dot green" /> Ответы {group.stats.answers_verified}/{group.stats.total}</span>
        <span><i class="dot violet" /> Helpers {group.stats.helpers_verified}/{group.stats.total}</span>
        <span><i class={`dot ${group.stats.errors ? "red" : "gray"}`} /> Ошибки {group.stats.errors}</span>
        {group.revision_requested && <span class="revision-chip"><i class="dot amber" /> Ждёт агента</span>}
        {group.task_url
          ? <a class="task-chip" href={group.task_url}><Icon>↗</Icon>{group.task}</a>
          : group.column === "queue"
            ? <button class="task-chip" onClick={openRegistration}><Icon>＋</Icon>Зарегистрировать</button>
            : <span class="task-chip task-disabled">Codex не связан</span>
        }
      </div>
      {editingTask && <div class="task-editor">
        <select value={selectedThreadId} onChange={(event) => setSelectedThreadId(event.currentTarget.value)}>
          <option value="">Создать новую · Terra · Medium</option>
          {codexTasks.map((task) => <option value={task.id} key={task.id}>{task.title}</option>)}
        </select>
        <button class="primary-button" onClick={registerGroup} disabled={registering}>
          {registering ? "Регистрирую…" : selectedThreadId ? "Связать и зарегистрировать" : "Создать и зарегистрировать"}
        </button>
        <button class="secondary-button" onClick={() => setEditingTask(false)} disabled={registering}>Отмена</button>
        {taskError && <span class="api-error">{taskError}</span>}
      </div>}

      <nav class="detail-tabs">
        {[["preview", "Проверка"], ["tasks", "Все задачи"], ["run", "Прогон"], ["issues", "Проблемы"], ["history", "История"]].map(([id, label]) => (
          <button class={tab === id ? "active" : ""} onClick={() => setTab(id)}>{label}</button>
        ))}
      </nav>

      <div class="detail-content">
        {tab === "preview" && (
          <>
            {previewState === "loading" && <div class="preview-state">Загружаю сохранённое превью…</div>}
            {previewState === "missing" && <div class="preview-state">
              {dryRun?.status === "queued" && "Тестовый прогон поставлен в очередь."}
              {dryRun?.status === "running" && "Тестовый прогон выполняется локально…"}
              {dryRun?.status === "failed" && "Тестовый прогон завершился с ошибкой. Положение карточки не изменилось."}
              {dryRun?.status === "skipped" && dryRun.message}
              {!dryRun?.status && "Нет актуального тестового прогона. Выбери режим внизу карточки."}
            </div>}
            {preview && <>
              <div class="sample-toolbar">
                <div class="sample-tabs">
                  {preview.samples.map((sample, index) => (
                    <button class={sampleIndex === index ? "active" : ""} onClick={() => setSampleIndex(index)} key={sample.problem_id}>
                      Задача {sample.source_problem_id}
                    </button>
                  ))}
                </div>
                <div class="sample-actions">
                  {selectedTask && <>
                    <button class="secondary-button" onClick={() => runProblem(selectedTask)} disabled={Boolean(runningProblemId || applyingProblemId)}>{runningProblemId === selectedTask.problem_id ? "Проверяю…" : "Проверить заново"}</button>
                    <button class="primary-button" onClick={() => applyProblem(selectedTask)} disabled={!canApplyTask(selectedTask, Boolean(runningProblemId || applyingProblemId))}>{applyingProblemId === selectedTask.problem_id ? "Записываю…" : isTaskRecorded(selectedTask) ? "Записано" : "Записать"}</button>
                    <button class="danger-button" onClick={() => rejectProblem(selectedTask)} disabled={selectedTask.problem_id === inventory.parent_problem_id || Boolean(rejectingProblemId)}>{rejectingProblemId === selectedTask.problem_id ? "Отклоняю…" : "Reject"}</button>
                  </>}
                  <button class="secondary-button" onClick={addSample} disabled={addingSample}>{addingSample ? "Добавляю…" : "+ Ещё задача"}</button>
                </div>
              </div>
              {sampleError && <div class="sample-error">{sampleError}</div>}
              <div class="sample-title">Задача {selectedSample.source_problem_id}</div>
              <div class="comparison-head">
                <div><span>Normalized до прогона</span><small>Сохранённый снимок задачи</small></div>
                <div><span>Локальный результат dry-run</span><small>Без записи через MCP</small></div>
              </div>
              <div class="comparison-grid">
                <ProblemPreview card={selectedSample.before} />
                {selectedSample.after
                  ? <ProblemPreview card={selectedSample.after} />
                  : <div class="preview-state">У этой задачи ещё нет успешного результата dry-run.</div>}
              </div>
            </>}
            <section class="review-box">
              <div class="review-title">Комментарий к группе</div>
              {comments.map((item) => <div class="comment" key={item.id}><span>Вы</span><p>{item.body}</p></div>)}
              <textarea value={comment} onInput={(event) => setComment(event.currentTarget.value)} placeholder="Что исправить в результате или раннере…" />
              <div class="review-actions">
                <span>Сохраняется локально в SQLite</span>
                <button class="primary-button" onClick={addComment}>Добавить комментарий</button>
              </div>
            </section>
            {runError && <div class="sample-error">{runError}</div>}
          </>
        )}
        {tab === "tasks" && <TaskInventory inventory={inventory} onOpenPreview={openTaskPreview} onRunProblem={runProblem} onApplyProblem={applyProblem} onRejectProblem={rejectProblem} runningProblemId={runningProblemId} applyingProblemId={applyingProblemId} rejectingProblemId={rejectingProblemId} />}
        {tab === "run" && <RunTab activity={activity} />}
        {tab === "issues" && <ProblemsTab activity={activity} inventory={inventory} onOpenProblem={openProblemPreview} onApplyProblem={applyProblem} runningProblemId={runningProblemId} applyingProblemId={applyingProblemId} />}
        {tab === "history" && <HistoryTab activity={activity} />}
      </div>

      <footer class="detail-footer">
        <span class="demo-label">{initialization?.status === "failed" ? `Initialize: ${initialization.error}` : "Данные и комментарии сохраняются локально"}</span>
        {initialization?.status === "failed" && <button class="secondary-button" onClick={retryInitialization}>Повторить Initialize</button>}
        <select value={dryRunMode} onChange={(event) => setDryRunMode(event.currentTarget.value)} disabled={["queued", "running"].includes(dryRun?.status)} aria-label="Режим тестового прогона">
          <option value="parent">Только родитель</option>
          <option value="random">Одна случайная задача</option>
          <option value="all">Вся группа</option>
        </select>
        <button class="secondary-button" onClick={startDryRun} disabled={!group.registered || ["queued", "running"].includes(dryRun?.status)}>
          {["queued", "running"].includes(dryRun?.status) ? "Выполняется…" : "Тестовый прогон"}
        </button>
        <button class="primary-button" onClick={applyGroup} disabled={!canApplyGroup(group, groupBusy)} title="После подтверждения запишет всю группу и выполнит Helpers с readback">
          {groupApplyActive ? "Применяю группу…" : "Одобрить и применить"}
        </button>
      </footer>
    </aside>
  );
}

function EmptyTab({ title, text }) {
  return <div class="empty-tab"><span class="empty-icon">≡</span><h3>{title}</h3><p>{text}</p></div>;
}

function AddGroupDialog({ catalogs, onClose, onCreate }) {
  const [id, setId] = useState("");
  const [catalogId, setCatalogId] = useState(catalogs[0]?.id || "");
  const [note, setNote] = useState("");
  const [existingSolutionPolicy, setExistingSolutionPolicy] = useState("preserve");
  const [conditionImagePolicy, setConditionImagePolicy] = useState("auto");
  const [solutionImagePolicy, setSolutionImagePolicy] = useState("auto");
  const [verifyAnswers, setVerifyAnswers] = useState(true);
  const [verifyHelpers, setVerifyHelpers] = useState(true);
  const [agentSampleSize, setAgentSampleSize] = useState(1);
  const submit = async (event) => {
    event.preventDefault();
    if (!id.trim() || !catalogId) return;
    await onCreate({
      id: id.trim(),
      catalog_id: catalogId,
      note: note.trim(),
      existing_solution_policy: existingSolutionPolicy,
      condition_image_policy: conditionImagePolicy,
      solution_image_policy: solutionImagePolicy,
      verify_answers: verifyAnswers,
      verify_helpers: verifyHelpers,
      agent_sample_size: agentSampleSize,
    });
  };
  return <div class="modal-layer">
    <button class="modal-scrim" onClick={onClose} aria-label="Закрыть" />
    <form class="add-dialog" onSubmit={submit}>
      <header><h2>Добавить группу</h2><button type="button" class="icon-button" onClick={onClose}>×</button></header>
      <label>Ключ группы<input value={id} onInput={(event) => setId(event.currentTarget.value)} placeholder="Например, 27719" autoFocus /></label>
      <label>UUID каталога
        <input
          value={catalogId}
          onInput={(event) => setCatalogId(event.currentTarget.value)}
          placeholder="Введите UUID каталога"
          required
        />
        <span class="catalog-suggestions">
          {catalogs.map((item) => (
            <button type="button" class={catalogId === item.id ? "selected" : ""} onClick={() => setCatalogId(item.id)} key={item.id}>
              <strong>{item.name}</strong><small>{item.id}</small>
            </button>
          ))}
        </span>
      </label>
      <label>Комментарий агенту<textarea value={note} onInput={(event) => setNote(event.currentTarget.value)} placeholder="Что проверить или учесть при регистрации…" /></label>
      <div class="policy-grid">
        <label>Существующее решение
          <select value={existingSolutionPolicy} onChange={(event) => setExistingSolutionPolicy(event.currentTarget.value)}>
            <option value="preserve">Сохранять</option><option value="rewrite">Переписывать</option>
          </select>
        </label>
        <label>Картинка условия
          <select value={conditionImagePolicy} onChange={(event) => setConditionImagePolicy(event.currentTarget.value)}>
            <option value="auto">Автоматически</option><option value="parent">Взять у родителя</option><option value="none">Не переносить</option>
          </select>
        </label>
        <label>Картинка решения
          <select value={solutionImagePolicy} onChange={(event) => setSolutionImagePolicy(event.currentTarget.value)}>
            <option value="auto">Автоматически</option><option value="parent">Взять у родителя</option><option value="none">Не переносить</option>
          </select>
        </label>
      </div>
      <div class="checks-row">
        <label><input type="checkbox" checked={verifyAnswers} onChange={(event) => setVerifyAnswers(event.currentTarget.checked)} /> Проверять ответы</label>
        <label><input type="checkbox" checked={verifyHelpers} onChange={(event) => setVerifyHelpers(event.currentTarget.checked)} /> Проверять Helpers</label>
      </div>
      <label class="sample-control">
        <span>Задач для просмотра агентом <b>{agentSampleSize}</b></span>
        <input type="range" min="1" max="3" value={agentSampleSize} onInput={(event) => setAgentSampleSize(Number(event.currentTarget.value))} />
      </label>
      <footer><button type="button" class="secondary-button" onClick={onClose}>Отмена</button><button class="primary-button" type="submit">Добавить</button></footer>
    </form>
  </div>;
}

function App() {
  const [groups, setGroups] = useState([]);
  const [search, setSearch] = useState("");
  const [catalogId, setCatalogId] = useState("all");
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const visibleGroups = useMemo(() => filterGroups(groups, { search, catalogId }), [groups, search, catalogId]);
  const selected = groups.find((group) => group.id === selectedId);
  const catalogs = useMemo(() => Array.from(new Map(
    groups
      .filter((group) => group.source_id && group.source_id !== "history")
      .map((group) => [group.source_id, { id: group.source_id, name: group.source }]),
  ).values()).sort((a, b) => a.name.localeCompare(b.name, "ru")), [groups]);
  const totals = useMemo(() => groups.reduce((result, group) => ({
    transformed: result.transformed + group.stats.transformed,
    helpers: result.helpers + group.stats.helpers,
    errors: result.errors + group.stats.errors,
  }), { transformed: 0, helpers: 0, errors: 0 }), [groups]);

  const loadGroups = async () => {
    try {
      const payload = await api.listGroups();
      setGroups(payload.groups);
      setError("");
    } catch {
      setError("Локальная API недоступна");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadGroups(); }, []);
  useEffect(() => {
    if (!groups.some((group) => group.column === "initialization")) return undefined;
    const timer = setInterval(loadGroups, 1500);
    return () => clearInterval(timer);
  }, [groups.some((group) => group.column === "initialization")]);

  const refresh = async () => {
    setLoading(true);
    try {
      await api.sync();
    } finally {
      await loadGroups();
    }
  };

  const createGroup = async (group) => {
    const created = await api.createGroup(group);
    setGroups((items) => [...items, created]);
    setAdding(false);
    setSelectedId(created.id);
  };

  const updateVisibleGroup = (updated) => {
    setGroups((items) => items.map((group) => group.id === updated.id ? updated : group));
  };

  const dropGroup = async (event, column) => {
    event.preventDefault();
    const id = event.dataTransfer.getData("text/group-id");
    setGroups(groups.map((group) => group.id === id ? { ...group, column } : group));
    try {
      const updated = await api.updateGroup(id, { column });
      setGroups((items) => items.map((group) => group.id === id ? updated : group));
    } catch {
      await loadGroups();
    }
  };

  return (
    <div class="app-shell">
      <header class="topbar">
        <div class="brand-mark">SR</div>
        <div class="title-block"><h1>Группы</h1><span>SolutionRunner</span></div>
        <div class="toolbar">
          <label class="search"><Icon>⌕</Icon><input value={search} onInput={(e) => setSearch(e.currentTarget.value)} placeholder="Группа, тема или путь" /></label>
          <select value={catalogId} onChange={(e) => setCatalogId(e.currentTarget.value)}>
            <option value="all">Все каталоги</option>{catalogs.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.id}</option>)}
          </select>
          <button class="secondary-button" onClick={refresh}>{loading ? "Обновление…" : "Обновить"}</button>
          <button class="primary-button" onClick={() => setAdding(true)}><Icon>＋</Icon>Добавить группу</button>
        </div>
      </header>

      <div class="summary-row">
        <span><b>{groups.length}</b> групп</span><span><b>{totals.transformed}</b> задач обработано</span><span><b>{totals.helpers}</b> Helpers ready</span><span class="summary-error"><b>{totals.errors}</b> требуют внимания</span>
        {error && <span class="api-error">{error}</span>}
      </div>

      <main class="board" aria-label="Канбан групп">
        {columns.map((column) => {
          const items = visibleGroups.filter((group) => group.column === column.id);
          return (
            <section key={column.id} class={`board-column tone-${column.tone}`} onDragOver={(e) => e.preventDefault()} onDrop={(e) => dropGroup(e, column.id)}>
              <header><h2>{column.title}</h2><span>{items.length}</span><button aria-label="Меню колонки">•••</button></header>
              <div class="column-list">
                {items.map((group) => <GroupCard key={group.id} group={group} onOpen={setSelectedId} onDragStart={(event, id) => event.dataTransfer.setData("text/group-id", id)} />)}
                {items.length === 0 && <div class="empty-column">Перетащите группу сюда</div>}
              </div>
            </section>
          );
        })}
      </main>

      {selected && <><button class="drawer-scrim" onClick={() => setSelectedId(null)} aria-label="Закрыть панель" /><DetailPanel group={selected} onClose={() => setSelectedId(null)} onGroupUpdate={updateVisibleGroup} /></>}
      {adding && <AddGroupDialog catalogs={catalogs} onClose={() => setAdding(false)} onCreate={createGroup} />}
    </div>
  );
}

render(<App />, document.getElementById("app"));
