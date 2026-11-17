import { useEffect, useState } from "preact/hooks";
import { createApi } from "./api.js";
import { CommentComposer } from "./comment-composer.jsx";
import { agentStatusLabels, Icon } from "./group-card.jsx";
import { HistoryTab, JobHistory, ProblemsTab, RunStatus, RunTab } from "./activity-tabs.jsx";
import { isHelpersReady, ProblemPreview, TaskInventory } from "./task-inventory.jsx";
import { canApplyGroup, canApplyTask, columns, isTaskRecorded, teacherHelperGroupUrl } from "./model.js";

const api = createApi();
const activeApplyStatuses = ["queued", "running", "retry_wait"];
export function DetailPanel({ group, onClose, onGroupUpdate, onRemove }) {
  const [removing, setRemoving] = useState(false);
  const [removeError, setRemoveError] = useState("");
  const removeGroup = async () => {
    if (!window.confirm(`Удалить «${group.title}» с доски? Комментарии карточки будут удалены. Исходные задачи, решения и история запусков сохранятся. Группу можно добавить заново.`)) return;
    setRemoving(true);
    setRemoveError("");
    try {
      await api.removeGroup(group.id);
      onRemove(group.id);
    } catch {
      setRemoveError("Не удалось удалить группу. Проверьте, что инициализация, агент и запуски завершены.");
    } finally {
      setRemoving(false);
    }
  };
  const teacherhelperUrl = teacherHelperGroupUrl(group.teacherhelper);
  const [tab, setTab] = useState("preview");
  const [comment, setComment] = useState("");
  const [comments, setComments] = useState([]);
  const [editingTask, setEditingTask] = useState(false);
  const [codexTasks, setCodexTasks] = useState([]);
  const [selectedThreadId, setSelectedThreadId] = useState("");
  const [registrationComment, setRegistrationComment] = useState("");
  const [registering, setRegistering] = useState(false);
  const [restartingAgent, setRestartingAgent] = useState(false);
  const [archivingCodex, setArchivingCodex] = useState(false);
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
  const [applyingHelpersProblemId, setApplyingHelpersProblemId] = useState(null);
  const [rejectingProblemId, setRejectingProblemId] = useState(null);
  const [initialization, setInitialization] = useState(null);
  const [inventory, setInventory] = useState(null);
  const [activity, setActivity] = useState(null);
  useEffect(() => {
    if (!["tasks", "issues"].includes(tab)) return;
    let active = true;
    const refresh = async () => {
      try {
        const next = await api.getTasks(group.id);
        if (active) setInventory(next);
      } catch { /* Keep the last successful view while reconnecting. */ }
    };
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => { active = false; clearInterval(timer); };
  }, [group.id, tab]);
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
    setApplyingHelpersProblemId(null);
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
    if (!applyRun || !activeApplyStatuses.includes(applyRun.status)) return undefined;
    const timer = setInterval(async () => {
      try {
        const state = await api.getApply(group.id);
        setApplyRun(state);
        if (!activeApplyStatuses.includes(state.status)) {
          setApplyingProblemId(null);
          setApplyingHelpersProblemId(null);
          if (state.status === "failed") {
            setRunError(state.stage === "helpers" ? "Не все Helpers удалось применить. Подробности — во вкладке «Проблемы»." : state.scope === "group" ? "Не все задачи группы удалось записать. Подробности — во вкладке «Проблемы»." : "Не удалось записать выбранную задачу.");
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
    } catch (error) {
      setRunError(`Не удалось запустить локальный тестовый прогон. ${error.message}`);
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
  const applyProblem = async (task, force = false) => {
    const action = force
      ? `Принудительно переписать решение задачи ${task.source_problem_id}? Настройка «Сохранять решение» будет проигнорирована.`
      : `Применить изменения только к задаче ${task.source_problem_id}?`;
    if (!window.confirm(action)) return;
    setRunError("");
    setApplyingProblemId(task.problem_id);
    try {
      setApplyRun(await api.applyProblem(group.id, task.problem_id, force));
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
  const applyHelpers = async (task) => {
    if (!window.confirm(`Применить только Helpers к задаче ${task.source_problem_id}?`)) return;
    setRunError("");
    setApplyingHelpersProblemId(task.problem_id);
    try {
      setApplyRun(await api.applyProblemHelpers(group.id, task.problem_id));
    } catch {
      setApplyingHelpersProblemId(null);
      setRunError("Не удалось запустить Helpers выбранной задачи.");
    }
  };
  const applyGroupHelpers = async () => {
    if (!window.confirm(`Применить Helpers ко всем задачам группы «${group.title}», где они ещё не готовы?`)) return;
    setRunError("");
    try {
      setApplyRun(await api.applyGroupHelpers(group.id));
    } catch {
      setRunError("Не удалось запустить Helpers группы.");
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
  const addComment = async (images = []) => {
    if (!comment.trim() && !images.length) return false;
    setRunError("");
    try {
      const result = await api.addComment(group.id, comment.trim(), null, images);
      setComments([...comments, result.comment]);
      onGroupUpdate(result.group);
      setComment("");
      return true;
    } catch (error) {
      setRunError(error.message || (group.codex_thread_id
        ? "Не удалось отправить комментарий в связанную Codex-задачу."
        : "Сначала свяжи группу с Codex-задачей."));
      return false;
    }
  };
  const addTaskComment = async (task, body, images = []) => {
    const result = await api.addComment(group.id, body, task.problem_id, images);
    setComments((items) => [...items, result.comment]);
    onGroupUpdate(result.group);
  };
  const restartAgent = async () => {
    setRestartingAgent(true);
    setRunError("");
    try {
      const result = await api.addComment(
        group.id,
        `Повторный запуск после блокировки: ${group.agent_summary || "продолжи работу над группой"}`,
      );
      setComments((items) => [...items, result.comment]);
      onGroupUpdate(result.group);
    } catch {
      setRunError("Не удалось перезапустить связанную Codex-задачу.");
    } finally {
      setRestartingAgent(false);
    }
  };
  const archiveCodex = async () => {
    setArchivingCodex(true);
    setRunError("");
    try {
      const result = await api.archiveCodex(group.id);
      onGroupUpdate(result.group);
    } catch {
      setRunError("Не удалось архивировать связанную Codex-задачу.");
    } finally {
      setArchivingCodex(false);
    }
  };
  const openRegistration = async () => {
    setEditingTask(true);
    setRegistrationComment("");
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
      const result = await api.registerGroup(
        group.id,
        selectedThreadId || null,
        selectedThreadId ? "" : registrationComment,
      );
      onGroupUpdate(result.group);
      setEditingTask(false);
    } catch (error) {
      setTaskError(error.message || "Не удалось зарегистрировать группу или создать Codex-задачу.");
    } finally {
      setRegistering(false);
    }
  };
  const retryInitialization = async () => {
    setInitialization(await api.startInitialization(group.id));
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
  const applyBusy = activeApplyStatuses.includes(applyRun?.status);
  const groupApplyActive = applyRun?.scope === "group" && applyRun?.stage !== "helpers" && applyBusy;
  const groupHelpersActive = applyRun?.scope === "group" && applyRun?.stage === "helpers" && applyBusy;
  const groupBusy = applyBusy || ["queued", "running"].includes(dryRun?.status);
  const latestDryRun = activity?.runs?.find((run) => run.kind === "dry-run");
  const latestApply = activity?.runs?.find((run) => run.kind === "apply");
  const columnTitle = columns.find((column) => column.id === group.column)?.title || group.column;
  const agentStatus = agentStatusLabels[group.agent_status];

  return (
    <aside class="detail-panel">
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

      {removeError && <p class="api-error" role="alert">{removeError}</p>}
      {editingTask && <div class="task-editor">
        <select value={selectedThreadId} onChange={(event) => setSelectedThreadId(event.currentTarget.value)}>
          <option value="">Создать новую · Sol 6.1 · Medium</option>
          {codexTasks.map((task) => <option value={task.id} key={task.id}>{task.title}</option>)}
        </select>
        <button class="primary-button" onClick={registerGroup} disabled={registering}>
          {registering ? "Регистрирую…" : selectedThreadId ? "Связать и зарегистрировать" : "Создать и зарегистрировать"}
        </button>
        <button class="secondary-button" onClick={() => setEditingTask(false)} disabled={registering}>Отмена</button>
        {!selectedThreadId && <textarea
          value={registrationComment}
          onInput={(event) => setRegistrationComment(event.currentTarget.value)}
          placeholder="Комментарий к новой задаче (необязательно)"
          rows="2"
        />}
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
                    <button class="primary-button" onClick={() => applyProblem(selectedTask)} disabled={!canApplyTask(selectedTask, Boolean(runningProblemId || applyingProblemId))}>{applyingProblemId === selectedTask.problem_id ? "Применяю…" : isTaskRecorded(selectedTask) ? "Применено" : "Применить"}</button>
                    <button class="danger-button" onClick={() => rejectProblem(selectedTask)} disabled={selectedTask.problem_id === inventory.parent_problem_id || Boolean(rejectingProblemId)}>{rejectingProblemId === selectedTask.problem_id ? "Отклоняю…" : "Reject"}</button>
                  </>}
                  <button class="secondary-button" onClick={addSample} disabled={addingSample}>{addingSample ? "Добавляю…" : "+ Ещё задача"}</button>
                </div>
              </div>
              {sampleError && <div class="sample-error">{sampleError}</div>}
              <div class="comparison-head">
                <div><span>Normalized до прогона</span></div>
                <div><span>{selectedSample.review_only ? "Рисунок для сверки — применение заблокировано" : "Локальный результат dry-run"}</span></div>
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
              {comments.map((item) => <div class={`comment comment-${item.author_type || "user"}`} key={item.id}><span>{item.author_type === "codex" ? "Codex" : "Вы"}</span><div><p>{item.body}</p><div class="comment-images">{(item.attachments || []).map((image) => <a href={image.url} target="_blank" rel="noreferrer"><img src={image.url} alt={image.name} /></a>)}</div></div></div>)}
              <CommentComposer key={group.id} value={comment} onChange={setComment} onSend={addComment} disabled={!group.codex_thread_id} placeholder="Что исправить в результате или раннере…" />
            </section>
          </>
        )}
        {tab === "tasks" && <TaskInventory inventory={inventory} onExpandPreview={(task) => api.getProblemPreview(group.id, task.problem_id)} onAddTaskComment={addTaskComment} canComment={Boolean(group.codex_thread_id)} onRunProblem={runProblem} onApplyProblem={applyProblem} onApplyHelpers={applyHelpers} onRejectProblem={rejectProblem} runningProblemId={runningProblemId} applyingProblemId={applyingProblemId} applyingHelpersProblemId={applyingHelpersProblemId} rejectingProblemId={rejectingProblemId} />}
        {tab === "run" && <RunTab activity={activity} />}
        {tab === "issues" && <ProblemsTab activity={activity} inventory={inventory} onOpenProblem={openProblemPreview} onApplyProblem={applyProblem} runningProblemId={runningProblemId} applyingProblemId={applyingProblemId} />}
        {tab === "history" && <><JobHistory groupId={group.id} /><HistoryTab activity={activity} /></>}
      </div>

      <footer class="detail-footer">
        {runError && <div class="sample-error" role="alert">{runError}</div>}
        {initialization?.status === "failed" && <span class="demo-label">Initialize: {initialization.error}</span>}
        {initialization?.status === "failed" && <button class="secondary-button" onClick={retryInitialization}>Повторить Initialize</button>}
        <select value={dryRunMode} onChange={(event) => setDryRunMode(event.currentTarget.value)} disabled={["queued", "running"].includes(dryRun?.status)} aria-label="Режим тестового прогона">
          <option value="parent">Только родитель</option>
          <option value="random">Одна случайная задача</option>
          <option value="all">Вся группа</option>
        </select>
        <button class="secondary-button" onClick={startDryRun} disabled={!group.registered || ["queued", "running"].includes(dryRun?.status)}>
          {["queued", "running"].includes(dryRun?.status) ? "Выполняется…" : "Тестовый прогон"}
        </button>
        <button class="secondary-button" onClick={applyGroupHelpers} disabled={groupBusy || !inventory?.tasks?.some((task) => !isHelpersReady(task) && (task.has_solution || ["applied", "already_complete"].includes(task.apply_status)))}>
          {groupHelpersActive ? "Helpers выполняются…" : "Helpers для всех"}
        </button>
        <button class="primary-button" onClick={applyGroup} disabled={!canApplyGroup(group, groupBusy)} title="После подтверждения запишет всю группу и выполнит Helpers с readback">
          {applyRun?.status === "retry_wait" ? `Повтор через ${applyRun.retry_in_seconds}с` : groupApplyActive ? "Применяю группу…" : "Одобрить и применить"}
        </button>
      </footer>
    </aside>
  );
}

