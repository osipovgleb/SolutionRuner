import { useEffect, useState } from "preact/hooks";

function useRegistration(api, group, onGroupUpdate) {
  const [editingTask, setEditingTask] = useState(false);
  const [codexTasks, setCodexTasks] = useState([]);
  const [selectedThreadId, setSelectedThreadId] = useState("");
  const [registrationComment, setRegistrationComment] = useState("");
  const [registering, setRegistering] = useState(false);
  const [taskError, setTaskError] = useState("");
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
  return { editingTask, setEditingTask, codexTasks, selectedThreadId, setSelectedThreadId,
    registrationComment, setRegistrationComment, registering, taskError, openRegistration, registerGroup };
}

export function useDetailThread(api, group, onGroupUpdate, setRunError) {
  const [comment, setComment] = useState("");
  const [comments, setComments] = useState([]);
  const registration = useRegistration(api, group, onGroupUpdate);
  const [restartingAgent, setRestartingAgent] = useState(false);
  const [archivingCodex, setArchivingCodex] = useState(false);
  useEffect(() => {
    api.listComments(group.id)
      .then(({ comments: items }) => setComments(items))
      .catch(() => setComments([]));
  }, [group.id]);
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
  return {
    comment, setComment, comments, restartingAgent, archivingCodex, addComment, addTaskComment,
    restartAgent, archiveCodex, ...registration,
  };
}
