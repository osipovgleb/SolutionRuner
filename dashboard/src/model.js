export const columns = [
  { id: "initialization", title: "Инициализация", tone: "blue" },
  { id: "queue", title: "На регистрацию", tone: "gray" },
  { id: "work", title: "В работе", tone: "amber" },
  { id: "issues", title: "Есть проблемы", tone: "red" },
  { id: "review", title: "На проверке", tone: "violet" },
  { id: "done", title: "Готово", tone: "green" },
];

export const compactCatalogLabel = (label) => label.replace(/^Каталог\s+/, "");

export const isTaskRecorded = (task) =>
  ["applied", "already_complete"].includes(task.apply_status)
  && ["applied", "already_complete"].includes(task.helpers_status);

export const canApplyTask = (task, busy = false) =>
  Boolean(task)
  && (task.dry_run_status === "ready" || Boolean(task.error))
  && !busy
  && !isTaskRecorded(task);

export const canApplyGroup = (group, busy = false) =>
  Boolean(group?.registered)
  && group.full_dry_run_status === "ready"
  && !busy;

const errorLabels = {
  "condition does not match a registered numeric rational expression": "Условие не подходит обработчику числовых рациональных выражений",
  "condition wording does not match square-root selector": "Формулировка условия не подходит обработчику квадратных корней",
  "ineligible upstream solution_answer:failed": "Решение или ответ не подготовлены: предыдущий этап завершился ошибкой",
};

export const formatTaskError = (error) => errorLabels[error] || error || "—";

export function teacherHelperGroupUrl(navigation) {
  if (!navigation) return null;
  const params = new URLSearchParams({
    source_site_id: navigation.source_site_id,
    snapshot_id: navigation.snapshot_id,
    category_id: navigation.category_id,
    theme_id: navigation.theme_id,
    group_id: navigation.group_id,
  });
  return `https://lessons-helper.ru/source-catalog/open?${params}`;
}

export function filterGroups(groups, { catalogId = "all", search = "" }) {
  const normalized = search.trim().toLocaleLowerCase("ru");
  return groups.filter((group) => {
    const sourceMatches = catalogId === "all" || group.source_id === catalogId;
    const haystack = `${group.id} ${group.title} ${group.path}`.toLocaleLowerCase("ru");
    return sourceMatches && (!normalized || haystack.includes(normalized));
  });
}
