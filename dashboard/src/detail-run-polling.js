import { useEffect } from "preact/hooks";

export function useInventoryPolling({ api, group, tab, setInventory }) {
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
}

export function useDryRunPolling({ api, group, dryRun, setDryRun, runningProblemId, loadPreview,
  setSampleIndex, setTab, setRunningProblemId, setAddingSample, setInventory,
  refreshActivity, onGroupUpdate, setRunError }) {
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
}

export function useApplyPolling({ api, group, applyRun, setApplyRun, setApplyingProblemId,
  setApplyingHelpersProblemId, setRunError, setInventory, refreshActivity,
  onGroupUpdate, activeApplyStatuses }) {
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
}
