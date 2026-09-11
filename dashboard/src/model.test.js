import test from "node:test";
import assert from "node:assert/strict";

import { canApplyGroup, canApplyTask, columns, compactCatalogLabel, filterGroups, formatTaskError, isTaskRecorded } from "./model.js";
import * as model from "./model.js";

test("initialization is the first kanban stage", () => {
  assert.equal(columns[0].id, "initialization");
  assert.deepEqual(columns.map((column) => column.id), [
    "initialization", "queue", "work", "issues", "review", "done",
  ]);
});

test("filters groups by catalog UUID and search text", () => {
  const groups = [
    { id: "27719", title: "Векторы и операции с ними", source_id: "catalog-main" },
    { id: "26661", title: "Иррациональные уравнения", source_id: "catalog-ege" },
  ];

  assert.deepEqual(filterGroups(groups, { catalogId: "catalog-main", search: "вектор" }), [groups[0]]);
});

test("kanban cards omit the catalog prefix from source labels", () => {
  assert.equal(compactCatalogLabel("Каталог ЕГЭ МАТ БАЗА"), "ЕГЭ МАТ БАЗА");
  assert.equal(compactCatalogLabel("История"), "История");
});

test("a failed Helpers step leaves an applied task retryable", () => {
  assert.equal(isTaskRecorded({ apply_status: "applied", helpers_status: "failed" }), false);
  assert.equal(isTaskRecorded({ apply_status: "applied", helpers_status: "applied" }), true);
  assert.equal(isTaskRecorded({ apply_status: "already_complete", helpers_status: "already_complete" }), true);
});

test("any task with an unresolved error can be applied again", () => {
  assert.equal(canApplyTask({ dry_run_status: "ready", apply_status: "applied", helpers_status: "failed" }), true);
  assert.equal(canApplyTask({ dry_run_status: "ready", apply_status: "applied", helpers_status: "applied" }), false);
  assert.equal(canApplyTask({ dry_run_status: "planned", apply_status: "failed", helpers_status: "skipped", error: "solution failed" }), true);
  assert.equal(canApplyTask({ dry_run_status: "planned", apply_status: "applied", helpers_status: "failed", error: "helpers failed" }), true);
  assert.equal(canApplyTask({ dry_run_status: "planned", apply_status: "planned", helpers_status: "planned" }), false);
});

test("whole-group apply requires a successful full-group dry-run", () => {
  assert.equal(canApplyGroup({ registered: true, full_dry_run_status: "ready" }), true);
  assert.equal(canApplyGroup({ registered: true, full_dry_run_status: "failed" }), false);
  assert.equal(canApplyGroup({ registered: true, full_dry_run_status: null }), false);
  assert.equal(canApplyGroup({ registered: true, full_dry_run_status: "ready" }, true), false);
});

test("technical pipeline failures are shown as useful Russian reasons", () => {
  assert.equal(
    formatTaskError("condition does not match a registered numeric rational expression"),
    "Условие не подходит обработчику числовых рациональных выражений",
  );
  assert.equal(
    formatTaskError("ineligible upstream solution_answer:failed"),
    "Решение или ответ не подготовлены: предыдущий этап завершился ошибкой",
  );
  assert.equal(
    formatTaskError("condition equation is ambiguous"),
    "В условии несколько или неоднозначная запись уравнения — раннер не смог однозначно определить, что решать",
  );
});

test("builds the TeacherHelper group link from every navigation id", () => {
  assert.equal(typeof model.teacherHelperGroupUrl, "function");
  assert.equal(
    model.teacherHelperGroupUrl({
      source_site_id: "site id",
      snapshot_id: "snapshot/id",
      category_id: "category?id",
      theme_id: "theme&id",
      group_id: "group id",
    }),
    "https://lessons-helper.ru/source-catalog/open?source_site_id=site+id&snapshot_id=snapshot%2Fid&category_id=category%3Fid&theme_id=theme%26id&group_id=group+id",
  );
  assert.match(
    model.teacherHelperGroupUrl({
      source_site_id: "4e79360f-d623-4d50-9e85-67858ac1bc85",
      snapshot_id: "41bc4d03-40cd-4407-8dea-df76e3f47ea8",
      category_id: "9c34b1ea-0cb8-4dc9-a841-3956f290d786",
      theme_id: "f598f433-d5cf-4ca7-af95-0d1cb6b52818",
      group_id: "940a61ed-f4c1-4dee-b1f2-4bf7b256f254",
    }),
    /source_site_id=4e79360f-d623-4d50-9e85-67858ac1bc85&snapshot_id=41bc4d03-40cd-4407-8dea-df76e3f47ea8/,
  );
});
