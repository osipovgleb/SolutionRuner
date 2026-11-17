import { useState } from "preact/hooks";
import { createApi } from "./api.js";
import { activeApplyStatuses, useDetailRuns } from "./detail-runs.js";
import { DetailPreview } from "./detail-preview.jsx";
import { DetailHeader } from "./detail-header.jsx";
import { useDetailThread } from "./detail-thread.js";
import { TaskRegistration } from "./task-registration.jsx";
import { HistoryTab, JobHistory, ProblemsTab, RunTab } from "./activity-tabs.jsx";
import { isHelpersReady, TaskInventory } from "./task-inventory.jsx";
import { canApplyGroup } from "./model.js";

const api = createApi();
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
  const {
    tab, setTab, preview, previewState, sampleIndex, setSampleIndex, addingSample,
    sampleError, dryRunMode, setDryRunMode, dryRun, runError, setRunError,
    runningProblemId, applyRun, applyingProblemId, applyingHelpersProblemId,
    rejectingProblemId, initialization, inventory, activity, startDryRun, addSample,
    runProblem, applyProblem, applyGroup, applyHelpers, applyGroupHelpers, rejectProblem,
    retryInitialization, openProblemPreview,
  } = useDetailRuns(api, group, onGroupUpdate);
  const {
    comment, setComment, comments, editingTask, setEditingTask, codexTasks,
    selectedThreadId, setSelectedThreadId, registrationComment, setRegistrationComment,
    registering, restartingAgent, archivingCodex, taskError, addComment, addTaskComment,
    restartAgent, archiveCodex, openRegistration, registerGroup,
  } = useDetailThread(api, group, onGroupUpdate, setRunError);
  const selectedSample = preview?.samples?.[sampleIndex];
  const selectedTask = inventory?.tasks?.find((task) => task.problem_id === selectedSample?.problem_id);
  const applyBusy = activeApplyStatuses.includes(applyRun?.status);
  const groupApplyActive = applyRun?.scope === "group" && applyRun?.stage !== "helpers" && applyBusy;
  const groupHelpersActive = applyRun?.scope === "group" && applyRun?.stage === "helpers" && applyBusy;
  const groupBusy = applyBusy || ["queued", "running"].includes(dryRun?.status);
  const latestDryRun = activity?.runs?.find((run) => run.kind === "dry-run");
  const latestApply = activity?.runs?.find((run) => run.kind === "apply");

  return (
    <aside class="detail-panel">
      <DetailHeader group={group} onClose={onClose} removeGroup={removeGroup} removing={removing} openRegistration={openRegistration} archiveCodex={archiveCodex} archivingCodex={archivingCodex} restartAgent={restartAgent} restartingAgent={restartingAgent} latestDryRun={latestDryRun} latestApply={latestApply} />

      {removeError && <p class="api-error" role="alert">{removeError}</p>}
      {editingTask && <TaskRegistration selectedThreadId={selectedThreadId} setSelectedThreadId={setSelectedThreadId} codexTasks={codexTasks} registerGroup={registerGroup} registering={registering} setEditingTask={setEditingTask} registrationComment={registrationComment} setRegistrationComment={setRegistrationComment} taskError={taskError} />}

      <nav class="detail-tabs">
        {[["preview", "Проверка"], ["tasks", "Все задачи"], ["run", "Прогон"], ["issues", "Проблемы"], ["history", "История"]].map(([id, label]) => (
          <button class={tab === id ? "active" : ""} onClick={() => setTab(id)}>{label}</button>
        ))}
      </nav>

      <div class="detail-content">
        {tab === "preview" && <DetailPreview group={group} previewState={previewState} dryRun={dryRun} preview={preview} sampleIndex={sampleIndex} setSampleIndex={setSampleIndex} selectedTask={selectedTask} selectedSample={selectedSample} inventory={inventory} runProblem={runProblem} applyProblem={applyProblem} rejectProblem={rejectProblem} runningProblemId={runningProblemId} applyingProblemId={applyingProblemId} rejectingProblemId={rejectingProblemId} addSample={addSample} addingSample={addingSample} sampleError={sampleError} comments={comments} comment={comment} setComment={setComment} addComment={addComment} />}
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

