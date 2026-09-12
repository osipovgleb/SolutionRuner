import test from "node:test";
import assert from "node:assert/strict";

import { createApi } from "./api.js";

test("dashboard API updates a group column", async () => {
  const calls = [];
  const api = createApi(async (url, options) => {
    calls.push([url, options]);
    return { ok: true, json: async () => ({ id: "27719", column: "review" }) };
  });

  const group = await api.updateGroup("27719", { column: "review" });

  assert.equal(group.column, "review");
  assert.equal(calls[0][0], "/api/groups/27719");
  assert.equal(calls[0][1].method, "PATCH");
});

test("dashboard API creates a registration candidate", async () => {
  const calls = [];
  const api = createApi(async (url, options) => {
    calls.push([url, options]);
    return { ok: true, json: async () => ({ id: "new-1", column: "queue" }) };
  });

  await api.createGroup({
    id: "new-1",
    catalog_id: "41bc4d03-40cd-4407-8dea-df76e3f47ea8",
    note: "Проверить картинку условия",
    agent_sample_size: 2,
  });

  assert.equal(calls[0][0], "/api/groups");
  assert.equal(calls[0][1].method, "POST");
  assert.equal(JSON.parse(calls[0][1].body).agent_sample_size, 2);
});

test("dashboard API includes a comment when creating a Codex task", async () => {
  const calls = [];
  const api = createApi(async (url, options) => {
    calls.push([url, options]);
    return { ok: true, json: async () => ({ task: { id: "thread-new" } }) };
  });

  await api.registerGroup("315122", null, "Проверь Helpers");

  assert.equal(calls[0][0], "/api/groups/315122/register");
  assert.deepEqual(JSON.parse(calls[0][1].body), { comment: "Проверь Helpers" });
});

test("dashboard API starts a scoped local dry-run", async () => {
  const calls = [];
  const api = createApi(async (url, options) => {
    calls.push([url, options]);
    return { ok: true, json: async () => ({ status: "queued", mode: "random" }) };
  });

  const state = await api.startDryRun("27719", "random");

  assert.equal(state.status, "queued");
  assert.equal(calls[0][0], "/api/groups/27719/dry-run");
  assert.equal(calls[0][1].method, "POST");
  assert.deepEqual(JSON.parse(calls[0][1].body), { mode: "random" });
});

test("dashboard API starts exact-problem and whole-group apply", async () => {
  const calls = [];
  const api = createApi(async (url, options) => {
    calls.push([url, options]);
    return { ok: true, json: async () => ({ status: "queued" }) };
  });

  await api.startProblemDryRun("27719", "problem-uuid");
  await api.applyProblem("27719", "problem-uuid");
  await api.applyGroup("27719");
  await api.applyProblemHelpers("27719", "problem-uuid");
  await api.applyGroupHelpers("27719");

  assert.equal(calls[0][0], "/api/groups/27719/dry-run");
  assert.deepEqual(JSON.parse(calls[0][1].body), {
    mode: "problem",
    problem_id: "problem-uuid",
  });
  assert.equal(calls[1][0], "/api/groups/27719/apply");
  assert.deepEqual(JSON.parse(calls[1][1].body), { problem_id: "problem-uuid" });
  assert.equal(calls[2][0], "/api/groups/27719/apply");
  assert.deepEqual(JSON.parse(calls[2][1].body), { scope: "group" });
  assert.deepEqual(JSON.parse(calls[3][1].body), { stage: "helpers", problem_id: "problem-uuid" });
  assert.deepEqual(JSON.parse(calls[4][1].body), { stage: "helpers", scope: "group" });
});

test("dashboard API reads initialization and task inventory", async () => {
  const calls = [];
  const api = createApi(async (url) => {
    calls.push(url);
    return { ok: true, json: async () => ({ status: "ready", tasks: [] }) };
  });

  await api.getInitialization("27719");
  await api.getTasks("27719");
  await api.getActivity("27719");

  assert.deepEqual(calls, [
    "/api/groups/27719/initialization",
    "/api/groups/27719/tasks",
    "/api/groups/27719/activity",
  ]);
});

test("dashboard API reads one exact problem preview", async () => {
  const calls = [];
  const api = createApi(async (url) => {
    calls.push(url);
    return { ok: true, json: async () => ({ samples: [] }) };
  });

  await api.getProblemPreview("27719", "problem-uuid");

  assert.deepEqual(calls, ["/api/groups/27719/tasks/problem-uuid/preview"]);
});

test("dashboard API rejects one exact problem with a reason", async () => {
  const calls = [];
  const api = createApi(async (url, options) => {
    calls.push([url, options]);
    return { ok: true, json: async () => ({ status: "rejected" }) };
  });

  await api.rejectProblem("27719", "problem-uuid", "Некорректное условие");

  assert.equal(calls[0][0], "/api/groups/27719/tasks/problem-uuid/reject");
  assert.equal(calls[0][1].method, "POST");
  assert.deepEqual(JSON.parse(calls[0][1].body), { reason: "Некорректное условие" });
});

test("dashboard API lists Codex tasks and registers a group", async () => {
  const calls = [];
  const api = createApi(async (url, options) => {
    calls.push([url, options]);
    return { ok: true, json: async () => ({ group: { id: "27719", codex_thread_id: "thread-1" } }) };
  });

  await api.listCodexTasks();
  await api.registerGroup("27719", "thread-1");
  await api.registerGroup("27720", null);
  await api.archiveCodex("27719");

  assert.equal(calls[0][0], "/api/codex/tasks");
  assert.equal(calls[1][0], "/api/groups/27719/register");
  assert.deepEqual(JSON.parse(calls[1][1].body), { thread_id: "thread-1" });
  assert.deepEqual(JSON.parse(calls[2][1].body), {});
  assert.equal(calls[3][0], "/api/groups/27719/archive-codex");
  assert.equal(calls[3][1].method, "POST");
});
