import { CommentComposer } from "./comment-composer.jsx";
import { ProblemPreview } from "./task-inventory.jsx";
import { canApplyTask, isTaskRecorded } from "./model.js";

export function DetailPreview({ group, previewState, dryRun, preview, sampleIndex, setSampleIndex, selectedTask, selectedSample, inventory, runProblem, applyProblem, rejectProblem, runningProblemId, applyingProblemId, rejectingProblemId, addSample, addingSample, sampleError, comments, comment, setComment, addComment }) {
  return (
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
  );
}
