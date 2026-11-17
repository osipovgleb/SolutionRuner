export function TaskRegistration({ selectedThreadId, setSelectedThreadId, codexTasks, registerGroup, registering, setEditingTask, registrationComment, setRegistrationComment, taskError }) {
  return (
      <div class="task-editor">
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
      </div>
  );
}
