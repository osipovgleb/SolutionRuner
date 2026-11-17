import test from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
import { renderPreviewHtml } from "./preview-html.js";

test("preview preserves formulas and diagrams while removing executable HTML", () => {
  const document = new JSDOM("<div id='preview'></div>").window.document;
  const element = document.querySelector("#preview");
  renderPreviewHtml(element, '<span data-inline-latex="x^2"></span><img data-asset-key="diagram" src="data:image/svg+xml;base64,PHN2Zy8+" onerror="alert(1)"><a href="javascript:alert(1)">link</a><script>alert(1)</script>');
  assert.equal(element.querySelector("span").dataset.inlineLatex, "x^2");
  assert.equal(element.querySelector("img").dataset.assetKey, "diagram");
  assert.match(element.querySelector("img").getAttribute("src"), /^data:image\/svg\+xml/);
  assert.equal(element.querySelector("img").hasAttribute("onerror"), false);
  assert.equal(element.querySelector("a").hasAttribute("href"), false);
  assert.equal(element.querySelector("script"), null);
});
