import { useEffect, useState } from "preact/hooks";
import { createPreviewActions, createApplyActions } from "./detail-run-actions.js";
import { useInventoryPolling, useDryRunPolling, useApplyPolling } from "./detail-run-polling.js";

export const activeApplyStatuses = ["queued", "running", "retry_wait"];

export function useDetailRuns(api, group, onGroupUpdate) {
  const [tab, setTab] = useState("preview");
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
  useInventoryPolling({ api, group, tab, setInventory });
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
  useDryRunPolling({ api, group, dryRun, setDryRun, runningProblemId, loadPreview,
    setSampleIndex, setTab, setRunningProblemId, setAddingSample, setInventory,
    refreshActivity, onGroupUpdate, setRunError });
  useApplyPolling({ api, group, applyRun, setApplyRun, setApplyingProblemId,
    setApplyingHelpersProblemId, setRunError, setInventory, refreshActivity,
    onGroupUpdate, activeApplyStatuses });
  const { startDryRun, addSample, runProblem, retryInitialization, openProblemPreview } = createPreviewActions({
    api, group, dryRunMode, setRunError, setDryRun, setAddingSample, setSampleError,
    setRunningProblemId, setInitialization, setPreview, setSampleIndex, setPreviewState, setTab,
  });
  const { applyProblem, applyGroup, applyHelpers, applyGroupHelpers, rejectProblem } = createApplyActions({
    api, group, setRunError, setApplyingProblemId, setApplyRun, setApplyingHelpersProblemId,
    setRejectingProblemId, setInventory, loadPreview, refreshActivity, onGroupUpdate, setTab,
  });
  return {
    tab, setTab, preview, previewState, sampleIndex, setSampleIndex, addingSample,
    sampleError, dryRunMode, setDryRunMode, dryRun, runError, setRunError,
    runningProblemId, applyRun, applyingProblemId, applyingHelpersProblemId,
    rejectingProblemId, initialization, inventory, activity, startDryRun, addSample,
    runProblem, applyProblem, applyGroup, applyHelpers, applyGroupHelpers, rejectProblem,
    retryInitialization, openProblemPreview,
  };
}
