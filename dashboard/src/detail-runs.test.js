import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { h, render } from "preact";
import { act } from "preact/test-utils";
import { useDetailRuns } from "./detail-runs.js";

test("run controls load the preview and start the selected mode", async () => {
  const dom = new JSDOM("<div id='root'></div>", { url: "http://localhost" });
  const oldWindow = globalThis.window;
  const oldDocument = globalThis.document;
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  const calls = [];
  let controls;
  const api = {
    getPreview: async () => ({ samples: [{ problem_id: "p1" }] }),
    getDryRun: async () => null,
    getInitialization: async () => null,
    getTasks: async () => ({ tasks: [] }),
    getActivity: async () => ({ runs: [] }),
    startDryRun: async (...args) => { calls.push(args); return { status: "queued" }; },
  };
  const group = { id: "g", title: "Group" };
  function Harness() {
    controls = useDetailRuns(api, group, () => {});
    return h("div");
  }
  const root = document.getElementById("root");
  try {
    await act(async () => { render(h(Harness), root); });
    await act(async () => { await Promise.resolve(); });
    assert.equal(controls.previewState, "ready");
    assert.equal(controls.preview.samples[0].problem_id, "p1");
    await act(async () => { controls.setDryRunMode("all"); });
    await act(async () => { await controls.startDryRun(); });
    assert.deepEqual(calls, [["g", "all"]]);
    assert.equal(controls.dryRun.status, "queued");
  } finally {
    render(null, root);
    dom.window.close();
    globalThis.window = oldWindow;
    globalThis.document = oldDocument;
  }
});
