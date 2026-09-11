async function request(fetcher, url, options = {}) {
  const response = await fetcher(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) throw new Error(`Dashboard API returned ${response.status}`);
  return response.json();
}

export function createApi(fetcher = fetch) {
  return {
    listGroups: () => request(fetcher, "/api/groups"),
    listCodexTasks: () => request(fetcher, "/api/codex/tasks"),
    registerGroup: (id, threadId = null) => request(fetcher, `/api/groups/${id}/register`, {
      method: "POST",
      body: JSON.stringify(threadId ? { thread_id: threadId } : {}),
    }),
    getGroup: (id) => request(fetcher, `/api/groups/${id}`),
    getInitialization: (id) => request(fetcher, `/api/groups/${id}/initialization`),
    startInitialization: (id) => request(fetcher, `/api/groups/${id}/initialization`, { method: "POST" }),
    getTasks: (id) => request(fetcher, `/api/groups/${id}/tasks`),
    getProblemPreview: (id, problemId) => request(fetcher, `/api/groups/${id}/tasks/${problemId}/preview`),
    rejectProblem: (id, problemId, reason) => request(fetcher, `/api/groups/${id}/tasks/${problemId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
    getActivity: (id) => request(fetcher, `/api/groups/${id}/activity`),
    createGroup: (group) => request(fetcher, "/api/groups", {
      method: "POST",
      body: JSON.stringify(group),
    }),
    sync: () => request(fetcher, "/api/sync", { method: "POST" }),
    updateGroup: (id, changes) => request(fetcher, `/api/groups/${id}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    }),
    listComments: (id) => request(fetcher, `/api/groups/${id}/comments`),
    getPreview: (id) => request(fetcher, `/api/groups/${id}/preview`),
    addPreviewSample: (id, sourceProblemId = null) => request(fetcher, `/api/groups/${id}/preview`, {
      method: "POST",
      body: JSON.stringify({ source_problem_id: sourceProblemId }),
    }),
    getDryRun: (id) => request(fetcher, `/api/groups/${id}/dry-run`),
    startDryRun: (id, mode) => request(fetcher, `/api/groups/${id}/dry-run`, {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),
    startProblemDryRun: (id, problemId) => request(fetcher, `/api/groups/${id}/dry-run`, {
      method: "POST",
      body: JSON.stringify({ mode: "problem", problem_id: problemId }),
    }),
    getApply: (id) => request(fetcher, `/api/groups/${id}/apply`),
    applyProblem: (id, problemId) => request(fetcher, `/api/groups/${id}/apply`, {
      method: "POST",
      body: JSON.stringify({ problem_id: problemId }),
    }),
    applyGroup: (id) => request(fetcher, `/api/groups/${id}/apply`, {
      method: "POST",
      body: JSON.stringify({ scope: "group" }),
    }),
    addComment: (id, body) => request(fetcher, `/api/groups/${id}/comments`, {
      method: "POST",
      body: JSON.stringify({ body }),
    }),
  };
}
