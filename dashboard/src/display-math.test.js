import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import katex from "katex";
import { readFileSync } from "node:fs";

test("display formulas retain horizontal overflow handling", () => {
  const dom = new JSDOM('<div class="teacher-content"><span data-formula-render-mode="display"></span><span></span></div>');
  const [display, inline] = dom.window.document.querySelectorAll(".teacher-content > span");
  const previousDocument = globalThis.document;
  globalThis.document = dom.window.document;
  try {
    katex.render("x^2", display, { displayMode: true });
    katex.render("x^2", inline, { displayMode: false });
  } finally {
    globalThis.document = previousDocument;
  }
  const selector = '.teacher-content [data-formula-render-mode="display"] > span';
  assert.equal(dom.window.document.querySelector(selector), display.querySelector(".katex-display"));
  assert.equal(inline.querySelector(selector), null);
  assert.match(readFileSync(new URL("./styles.css", import.meta.url), "utf8"), /\[data-formula-render-mode="display"\] > span\s*\{\s*overflow-x: auto;\s*overflow-y: hidden;/);
});
