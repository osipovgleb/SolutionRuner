import createDOMPurify from "dompurify";

/** Render a preview safely while keeping the data attributes needed by KaTeX. */
export function renderPreviewHtml(element, html) {
  const DOMPurify = createDOMPurify(element.ownerDocument.defaultView);
  element.innerHTML = DOMPurify.sanitize(html || "");
}
