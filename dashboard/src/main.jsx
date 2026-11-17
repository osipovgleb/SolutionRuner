import { render } from "preact";
import { useEffect, useMemo, useState } from "preact/hooks";
import "katex/dist/katex.min.css";
import { createApi } from "./api.js";
import { AddGroupDialog } from "./add-group-dialog.jsx";
import { GroupCard, Icon } from "./group-card.jsx";
import { DetailPanel } from "./detail-panel.jsx";
import { columns, filterGroups } from "./model.js";
import "./styles.css";

const api = createApi();
function App() {
  const [groups, setGroups] = useState([]);
  const [catalogRegistry, setCatalogRegistry] = useState([]);
  const [search, setSearch] = useState("");
  const [catalogId, setCatalogId] = useState("all");
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const visibleGroups = useMemo(() => filterGroups(groups, { search, catalogId }), [groups, search, catalogId]);
  const selected = groups.find((group) => group.id === selectedId);
  const catalogs = useMemo(() => Array.from(new Map([
    ...groups
      .filter((group) => group.source_id && group.source_id !== "history")
      .map((group) => [group.source_id, { id: group.source_id, name: group.source }]),
    ...catalogRegistry.map((item) => [item.id, item]),
  ]).values()).sort((a, b) => a.name.localeCompare(b.name, "ru")), [groups, catalogRegistry]);
  const loadGroups = async () => {
    try {
      const payload = await api.listGroups();
      setGroups(payload.groups);
      setCatalogRegistry(payload.catalogs || []);
      setError("");
    } catch {
      setError("Локальная API недоступна");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadGroups(); }, []);
  useEffect(() => {
    if (!groups.some((group) => ["initialization", "jobs"].includes(group.column) || ["working", "verifying"].includes(group.agent_status))) return undefined;
    const timer = setInterval(loadGroups, 1500);
    return () => clearInterval(timer);
  }, [groups.some((group) => ["initialization", "jobs"].includes(group.column) || ["working", "verifying"].includes(group.agent_status))]);

  const refresh = async () => {
    setLoading(true);
    try {
      await api.sync();
    } finally {
      await loadGroups();
    }
  };

  const createGroup = async (group) => {
    const created = await api.createGroup(group);
    setGroups((items) => [...items, created]);
    setAdding(false);
    setSelectedId(created.id);
  };

  const updateVisibleGroup = (updated) => {
    setGroups((items) => items.map((group) => group.id === updated.id ? updated : group));
  };

  const dropGroup = async (event, column) => {
    event.preventDefault();
    const id = event.dataTransfer.getData("text/group-id");
    setGroups(groups.map((group) => group.id === id ? { ...group, column } : group));
    try {
      const updated = await api.updateGroup(id, { column });
      setGroups((items) => items.map((group) => group.id === id ? updated : group));
    } catch {
      await loadGroups();
    }
  };

  return (
    <div class="app-shell">
      <header class="topbar">
        <div class="toolbar">
          <label class="search"><Icon>⌕</Icon><input value={search} onInput={(e) => setSearch(e.currentTarget.value)} placeholder="Группа, тема или путь" /></label>
          <select value={catalogId} onChange={(e) => setCatalogId(e.currentTarget.value)}>
            <option value="all">Все каталоги</option>{catalogs.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.id}</option>)}
          </select>
          <button class="secondary-button" onClick={refresh}>{loading ? "Обновление…" : "Обновить"}</button>
          <button class="primary-button" onClick={() => setAdding(true)}><Icon>＋</Icon>Добавить группу</button>
        </div>
      </header>

      <main class="board" aria-label="Канбан групп">
        {columns.map((column) => {
          const items = visibleGroups.filter((group) => group.column === column.id);
          return (
            <section
              key={column.id}
              class={`board-column tone-${column.tone}`}
              onDragOver={column.system ? undefined : (e) => e.preventDefault()}
              onDrop={column.system ? undefined : (e) => dropGroup(e, column.id)}
            >
              <header><h2>{column.title}</h2><span>{items.length}</span></header>
              <div class="column-list">
                {items.map((group) => <GroupCard key={group.id} group={group} onOpen={setSelectedId} onDragStart={(event, id) => event.dataTransfer.setData("text/group-id", id)} />)}
                {items.length === 0 && <div class="empty-column">{column.system ? "Запусков нет" : "Перетащите группу сюда"}</div>}
              </div>
            </section>
          );
        })}
      </main>

      {selected && <><button class="drawer-scrim" onClick={() => setSelectedId(null)} aria-label="Закрыть панель" /><DetailPanel group={selected} onClose={() => setSelectedId(null)} onGroupUpdate={updateVisibleGroup} onRemove={(id) => { setGroups((items) => items.filter((item) => item.id !== id)); setSelectedId(null); }} /></>}
      {adding && <AddGroupDialog catalogs={catalogs} onClose={() => setAdding(false)} onCreate={createGroup} />}
    </div>
  );
}

render(<App />, document.getElementById("app"));
