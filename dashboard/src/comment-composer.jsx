import { useState } from "preact/hooks";

export function CommentComposer({ value, onChange, onSend, disabled, placeholder }) {
  const [images, setImages] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const attach = async (files) => {
    if (disabled || busy || reading) return;
    const selected = Array.from(files);
    setError("");
    if (selected.length + images.length > 4 || selected.some((file) => !["image/png", "image/jpeg", "image/gif", "image/webp"].includes(file.type) || file.size > 5 * 1024 * 1024)) {
      setError("До 4 изображений PNG, JPEG, GIF или WebP, каждое до 5 МБ.");
      return;
    }
    setReading(true);
    try {
      const additions = await Promise.all(selected.map((file) => new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve({ name: file.name, preview: reader.result, data: String(reader.result).split(",")[1] });
        reader.onerror = () => reject(new Error("Не удалось прочитать изображение."));
        reader.readAsDataURL(file);
      })));
      setImages((current) => [...current, ...additions]);
    } catch (failure) { setError(failure.message); }
    finally { setReading(false); }
  };
  const send = async () => {
    setBusy(true); setError("");
    try {
      const accepted = await onSend(images.map(({name, data}) => ({name, data})));
      if (accepted !== false) setImages([]);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  };
  return <div class={`comment-composer${dragging ? " dragging" : ""}`}
    onDragOver={(event) => { event.preventDefault(); if (!disabled) setDragging(true); }}
    onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false); }}
    onDrop={(event) => { event.preventDefault(); setDragging(false); attach(event.dataTransfer.files); }}>
    <textarea value={value} onInput={(event) => onChange(event.currentTarget.value)} placeholder={placeholder}
      disabled={disabled || busy} onPaste={(event) => {
        const files = Array.from(event.clipboardData?.files || []);
        if (files.length) { event.preventDefault(); attach(files); }
      }} />
    {!!images.length && <div class="comment-images">{images.map((item, index) => <div>
      <img src={item.preview} alt={item.name} /><button type="button" disabled={busy} aria-label={`Удалить ${item.name}`} onClick={() => setImages((items) => items.filter((_, i) => i !== index))}>×</button>
    </div>)}</div>}
    <div class="comment-compose-actions"><label class="secondary-button">Прикрепить картинки<input type="file" accept="image/png,image/jpeg,image/gif,image/webp" multiple disabled={disabled || busy || reading} onChange={(event) => { attach(event.currentTarget.files); event.currentTarget.value = ""; }} /></label>
      <span>или перетащите сюда</span><button class="primary-button" onClick={send} disabled={disabled || busy || reading || (!value.trim() && !images.length)}>{busy ? "Отправляю…" : "Отправить в Codex"}</button></div>
    {error && <p class="sample-error" role="alert">{error}</p>}
  </div>;
}
