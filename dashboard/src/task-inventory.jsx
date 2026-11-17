import { useEffect, useRef, useState } from "preact/hooks";
import katex from "katex";
import { CommentComposer } from "./comment-composer.jsx";
import { renderPreviewHtml } from "./preview-html.js";
import { canApplyTask, formatTaskError, isTaskRecorded } from "./model.js";

export const isHelpersReady = (task) => ["applied", "already_complete"].includes(task.helpers_status);

function HtmlSection({ html }) {
  const element = useRef(null);
  useEffect(() => {
    if (!element.current) return;
    renderPreviewHtml(element.current, html);
    element.current.querySelectorAll("[data-inline-latex]").forEach((node) => {
      katex.render(node.dataset.inlineLatex || "", node, {
        throwOnError: false,
        displayMode: node.dataset.formulaRenderMode === "display",
      });
    });
  }, [html]);
  return <div ref={element} class="teacher-content" />;
}

export function ProblemPreview({ card }) {
  return (
    <article class="problem-preview">
      <HtmlSection html={card.condition_html} />
      {card.solution_html && <><div class="solution-label">Решение</div><HtmlSection html={card.solution_html} /></>}
      {card.answer_html && <div class="preview-answer"><strong>Ответ:</strong><HtmlSection html={card.answer_html} /></div>}
    </article>
  );
}

function StageStatus({ status, error }) {
  return <td class="stage-status">
    <span>{status || "—"}</span>
    {error && <small title={formatTaskError(error)}>{formatTaskError(error)}</small>}
  </td>;
}

export function TaskInventory({ inventory, onExpandPreview, onAddTaskComment, canComment, onRunProblem, onApplyProblem, onApplyHelpers, onRejectProblem, runningProblemId, applyingProblemId, applyingHelpersProblemId, rejectingProblemId }) {
  const [filter, setFilter] = useState("all");
  const [expandedProblemId, setExpandedProblemId] = useState(null);
  const [expandedPreview, setExpandedPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [taskComment, setTaskComment] = useState("");
  const [commentingProblemId, setCommentingProblemId] = useState(null);
  const [taskCommentError, setTaskCommentError] = useState("");
  if (!inventory) return <div class="preview-state">Состав группы ещё не инициализирован.</div>;
  const togglePreview = async (task) => {
    if (expandedProblemId === task.problem_id) {
      setExpandedProblemId(null);
      return;
    }
    setExpandedProblemId(task.problem_id);
    setExpandedPreview(null);
    setPreviewLoading(true);
    try {
      setExpandedPreview(await onExpandPreview(task));
    } finally {
      setPreviewLoading(false);
    }
  };
  const visible = inventory.tasks.filter((task) => {
    if (filter === "errors") return Boolean(task.error);
    if (filter === "ready") return [task.dry_run_status, task.apply_status, task.helpers_status].includes("ready") || task.helpers_status === "applied";
    if (filter === "skipped") return [task.dry_run_status, task.apply_status, task.helpers_status].includes("skipped");
    return true;
  });
  const addTaskComment = async (task, images = []) => {
    if (!taskComment.trim() && !images.length) return false;
    setCommentingProblemId(task.problem_id);
    setTaskCommentError("");
    try {
      await onAddTaskComment(task, taskComment.trim(), images);
      setTaskComment("");
      return true;
    } catch (error) {
      setTaskCommentError(error.message || "Не удалось отправить комментарий в Codex.");
      return false;
    } finally {
      setCommentingProblemId(null);
    }
  };
  return <section class="task-inventory">
    <div class="inventory-toolbar">
      <strong>{inventory.tasks.length} задач</strong>
      <div>{[["all", "Все"], ["ready", "Готовы"], ["skipped", "Пропущены"], ["errors", "Ошибки"]].map(([id, label]) =>
        <button class={filter === id ? "active" : ""} onClick={() => setFilter(id)}>{label}</button>
      )}</div>
    </div>
    <div class="inventory-table-wrap"><table class="inventory-table">
      <thead><tr><th>Задача</th><th>Разделы</th><th>Картинки условия</th><th>Картинки решения</th><th>Последний dry-run</th><th>Последний Apply</th><th>Helpers</th><th>Причина Apply</th><th>Действия</th></tr></thead>
      <tbody>{visible.map((task) => {
        const conditionAssets = task.assets.filter((asset) => asset.section === "condition");
        const solutionAssets = task.assets.filter((asset) => asset.section === "solution");
        const recorded = isTaskRecorded(task);
        const expanded = expandedProblemId === task.problem_id;
        const sample = expandedPreview?.samples?.[0];
        return <>
        <tr onClick={() => togglePreview(task)} class={`${task.problem_id === inventory.parent_problem_id ? "parent-task " : ""}${expanded ? "expanded-task" : ""}`}>
          <td><button onClick={(event) => { event.stopPropagation(); togglePreview(task); }}>{expanded ? "▾" : "▸"} Задача {task.source_problem_id}</button>{task.problem_id === inventory.parent_problem_id && <small>родитель</small>}</td>
          <td>{task.has_condition ? "У" : "—"} · {task.has_solution ? "Р" : "—"} · {task.has_answer ? "О" : "—"}</td>
          <td>{conditionAssets.map((asset) => asset.content_type.replace("image/", "")).join(", ") || "—"}</td>
          <td>{solutionAssets.map((asset) => asset.content_type.replace("image/", "")).join(", ") || "—"}</td>
          <StageStatus status={task.dry_run_status} error={task.dry_run_error} /><StageStatus status={task.apply_status} error={task.error || task.apply_error} /><td>{task.helpers_status || "—"}</td><td>{formatTaskError(task.error || task.apply_error)}</td>
          <td><div class="task-actions">
            <button class="secondary-button" onClick={(event) => { event.stopPropagation(); onRunProblem(task); }} disabled={Boolean(runningProblemId || applyingProblemId || applyingHelpersProblemId)}>
              {runningProblemId === task.problem_id ? "Проверяю…" : "Проверить"}
            </button>
            <button class="primary-button" onClick={(event) => { event.stopPropagation(); onApplyProblem(task); }} disabled={!canApplyTask(task, Boolean(runningProblemId || applyingProblemId || applyingHelpersProblemId))}>
              {applyingProblemId === task.problem_id ? "Применяю…" : recorded ? "Применено" : "Применить"}
            </button>
            {recorded && <button class="secondary-button" onClick={(event) => { event.stopPropagation(); onApplyProblem(task, true); }} disabled={Boolean(runningProblemId || applyingProblemId || applyingHelpersProblemId)}>
              Применить принудительно
            </button>}
            <button class="secondary-button" onClick={(event) => { event.stopPropagation(); onApplyHelpers(task); }} disabled={isHelpersReady(task) || !(task.has_solution || ["applied", "already_complete"].includes(task.apply_status)) || Boolean(runningProblemId || applyingProblemId || applyingHelpersProblemId)}>
              {applyingHelpersProblemId === task.problem_id ? "Helpers…" : isHelpersReady(task) ? "Helpers готовы" : "Helpers"}
            </button>
            <button class="danger-button" title={task.problem_id === inventory.parent_problem_id ? "Родитель отклоняется только вместе с группой" : ""} onClick={(event) => { event.stopPropagation(); onRejectProblem(task); }} disabled={task.problem_id === inventory.parent_problem_id || Boolean(runningProblemId || applyingProblemId || applyingHelpersProblemId || rejectingProblemId)}>
              {rejectingProblemId === task.problem_id ? "Отклоняю…" : "Reject"}
            </button>
          </div></td>
        </tr>
        {expanded && <tr class="inventory-preview-row"><td colSpan="9">
          {previewLoading && <div class="preview-state">Загружаю карточки…</div>}
          {!previewLoading && sample && <div class="inline-comparison">
            <div class="comparison-head"><div><span>Исходная карточка</span><small>Normalized-контент</small></div><div><span>{sample.review_only ? "Рисунок для сверки" : "Подготовленная карточка"}</span><small>{sample.review_only ? "Применение заблокировано" : "Результат последнего dry-run"}</small></div></div>
            <div class="comparison-grid"><ProblemPreview card={sample.before} />{sample.after ? <ProblemPreview card={sample.after} /> : <div class="preview-state">Для этой задачи нет подготовленной карточки в последнем dry-run.</div>}</div>
          </div>}
          {!previewLoading && !sample && <div class="preview-state">Карточка недоступна.</div>}
          <div class="task-comment-box">
            <CommentComposer key={task.problem_id} value={taskComment} onChange={setTaskComment} placeholder="Комментарий по этой задаче…" disabled={!canComment || commentingProblemId === task.problem_id} onSend={(images) => addTaskComment(task, images)} />
            {taskCommentError && <p class="sample-error">{taskCommentError}</p>}
          </div>
        </td></tr>}
        </>;
      })}</tbody>
    </table></div>
  </section>;
}

