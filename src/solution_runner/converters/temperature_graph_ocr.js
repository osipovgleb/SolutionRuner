#!/usr/bin/env node
/** Read prepared tick/date crops with one reused Tesseract worker. */

const fs = require("node:fs");
const { createWorker, PSM } = require("tesseract.js");

async function main() {
  const request = JSON.parse(fs.readFileSync(0, "utf8"));
  const worker = await createWorker("rus+eng");
  const ticks = [];
  try {
    await worker.setParameters({
      tessedit_pageseg_mode: PSM.SINGLE_LINE,
      tessedit_char_whitelist: "-0123456789,.",
    });
    for (const path of request.tick_paths) {
      const result = await worker.recognize(path);
      ticks.push(result.data.text.trim());
    }
    await worker.setParameters({
      tessedit_pageseg_mode: PSM.SPARSE_TEXT,
      tessedit_char_whitelist: "",
      preserve_interword_spaces: "1",
    });
    const dates = await worker.recognize(request.date_path);
    process.stdout.write(JSON.stringify({ ticks, dates: dates.data.text }));
  } finally {
    await worker.terminate();
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
