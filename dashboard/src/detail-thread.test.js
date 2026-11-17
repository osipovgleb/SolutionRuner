import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { h, render } from "preact";
import { act } from "preact/test-utils";
import { useDetailThread } from "./detail-thread.js";

test("thread controls load comments and register the selected chat", async () => {
  const dom = new JSDOM("<div id='root'></div>", { url: "http://localhost" });
  const oldWindow = globalThis.window;
  const oldDocument = globalThis.document;
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  const calls = [];
  const updated = [];
  let controls;
  const api = {
    listComments: async () => ({ comments: [{ id: "old" }] }),
    listCodexTasks: async () => ({ tasks: [{ id: "thread-1" }] }),
    registerGroup: async (...args) => { calls.push(args); return { group: { id: "g" } }; },
  };
  const group = { id: "g" };
  function Harness() {
    controls = useDetailThread(api, group, (value) => updated.push(value), () => {});
    return h("div");
  }
  const root = document.getElementById("root");
  try {
    await act(async () => { render(h(Harness), root); });
    await act(async () => { await Promise.resolve(); });
    assert.equal(controls.comments[0].id, "old");
    await act(async () => { await controls.openRegistration(); });
    assert.equal(controls.editingTask, true);
    assert.equal(controls.codexTasks[0].id, "thread-1");
    await act(async () => { controls.setSelectedThreadId("thread-1"); });
    await act(async () => { await controls.registerGroup(); });
    assert.deepEqual(calls, [["g", "thread-1", ""]]);
    assert.equal(controls.editingTask, false);
    assert.deepEqual(updated, [{ id: "g" }]);
  } finally {
    render(null, root);
    dom.window.close();
    globalThis.window = oldWindow;
    globalThis.document = oldDocument;
  }
});
