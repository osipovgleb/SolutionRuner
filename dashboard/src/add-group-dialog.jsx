import { useState } from "preact/hooks";

export function AddGroupDialog({ catalogs, onClose, onCreate }) {
  const [id, setId] = useState("");
  const [catalogId, setCatalogId] = useState(catalogs[0]?.id || "");
  const [note, setNote] = useState("");
  const [existingSolutionPolicy, setExistingSolutionPolicy] = useState("preserve");
  const [conditionImagePolicy, setConditionImagePolicy] = useState("auto");
  const [solutionImagePolicy, setSolutionImagePolicy] = useState("auto");
  const [verifyAnswers, setVerifyAnswers] = useState(true);
  const [verifyHelpers, setVerifyHelpers] = useState(true);
  const [agentSampleSize, setAgentSampleSize] = useState(1);
  const submit = async (event) => {
    event.preventDefault();
    if (!id.trim() || !catalogId) return;
    await onCreate({
      id: id.trim(),
      catalog_id: catalogId,
      note: note.trim(),
      existing_solution_policy: existingSolutionPolicy,
      condition_image_policy: conditionImagePolicy,
      solution_image_policy: solutionImagePolicy,
      verify_answers: verifyAnswers,
      verify_helpers: verifyHelpers,
      agent_sample_size: agentSampleSize,
    });
  };
  return <div class="modal-layer">
    <button class="modal-scrim" onClick={onClose} aria-label="Закрыть" />
    <form class="add-dialog" onSubmit={submit}>
      <header><h2>Добавить группу</h2><button type="button" class="icon-button" onClick={onClose}>×</button></header>
      <label>Номер группы<input value={id} onInput={(event) => setId(event.currentTarget.value)} placeholder="Например, 506803 или Группа 506803" autoFocus /></label>
      <label>UUID каталога
        <input
          value={catalogId}
          onInput={(event) => setCatalogId(event.currentTarget.value)}
          placeholder="Введите UUID каталога"
          required
        />
        <span class="catalog-suggestions">
          {catalogs.map((item) => (
            <button type="button" class={catalogId === item.id ? "selected" : ""} onClick={() => setCatalogId(item.id)} key={item.id}>
              <strong>{item.name}</strong><small>{item.id}</small>
            </button>
          ))}
        </span>
      </label>
      <label>Комментарий агенту<textarea value={note} onInput={(event) => setNote(event.currentTarget.value)} placeholder="Что проверить или учесть при регистрации…" /></label>
      <div class="policy-grid">
        <label>Существующее решение
          <select value={existingSolutionPolicy} onChange={(event) => setExistingSolutionPolicy(event.currentTarget.value)}>
            <option value="preserve">Сохранять</option><option value="rewrite">Переписывать</option>
          </select>
        </label>
        <label>Картинка условия
          <select value={conditionImagePolicy} onChange={(event) => setConditionImagePolicy(event.currentTarget.value)}>
            <option value="auto">Автоматически</option><option value="parent">Взять у родителя</option><option value="none">Не переносить</option>
          </select>
        </label>
        <label>Картинка решения
          <select value={solutionImagePolicy} onChange={(event) => setSolutionImagePolicy(event.currentTarget.value)}>
            <option value="auto">Автоматически</option><option value="parent">Взять у родителя</option><option value="none">Не переносить</option>
          </select>
        </label>
      </div>
      <div class="checks-row">
        <label><input type="checkbox" checked={verifyAnswers} onChange={(event) => setVerifyAnswers(event.currentTarget.checked)} /> Проверять ответы</label>
        <label><input type="checkbox" checked={verifyHelpers} onChange={(event) => setVerifyHelpers(event.currentTarget.checked)} /> Проверять Helpers</label>
      </div>
      <label class="sample-control">
        <span>Задач для просмотра агентом <b>{agentSampleSize}</b></span>
        <input type="range" min="1" max="3" value={agentSampleSize} onInput={(event) => setAgentSampleSize(Number(event.currentTarget.value))} />
      </label>
      <footer><button type="button" class="secondary-button" onClick={onClose}>Отмена</button><button class="primary-button" type="submit">Добавить</button></footer>
    </form>
  </div>;
}

