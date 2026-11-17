export function createPreviewActions({ api, group, dryRunMode, setRunError, setDryRun, setAddingSample,
  setSampleError, setRunningProblemId, setInitialization, setPreview, setSampleIndex, setPreviewState, setTab }) {
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
  return { startDryRun, addSample, runProblem, retryInitialization, openProblemPreview };
}

export function createApplyActions({ api, group, setRunError, setApplyingProblemId, setApplyRun,
  setApplyingHelpersProblemId, setRejectingProblemId, setInventory, loadPreview,
  refreshActivity, onGroupUpdate, setTab }) {
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
  return { applyProblem, applyGroup, applyHelpers, applyGroupHelpers, rejectProblem };
}
