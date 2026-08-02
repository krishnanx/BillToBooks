import { useRef } from "react";

const MODEL_OPTIONS = [
  { id: "gemini", label: "Gemini" },
  { id: "claude", label: "Claude" },
  { id: "openai", label: "OpenAI" },
];

export default function UploadPanel({
  file, onFile, previewUrl,
  selectedModels, onToggleModel,
  onExtract, loading, statusText,
}) {
  const inputRef = useRef(null);

  return (
    <section className="sheet">
      <div className="sheet-tab">01</div>
      <h2>Upload a bill</h2>
      <p className="hint">A clear photo of a handwritten or printed receipt.</p>

      <div
        className="dropzone"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files?.[0];
          if (f) onFile(f);
        }}
      >
        {previewUrl ? (
          <img src={previewUrl} alt="Bill preview" className="preview" />
        ) : (
          <span>Click or drag a photo here</span>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
      />

      <h3 className="sub-label">Models to compare</h3>
      <div className="chip-row">
        {MODEL_OPTIONS.map((m) => (
          <label key={m.id} className={`chip ${selectedModels.includes(m.id) ? "chip-active" : ""}`}>
            <input
              type="checkbox"
              checked={selectedModels.includes(m.id)}
              onChange={() => onToggleModel(m.id)}
            />
            {m.label}
          </label>
        ))}
      </div>
      <p className="hint">Only models with a key set in backend/.env will run.</p>

      <div className="action-row">
        <button className="btn-stamp" disabled={!file || loading} onClick={onExtract}>
          {loading ? "Reading bill…" : "Extract bill data"}
        </button>
        {statusText && <span className="status-text">{statusText}</span>}
      </div>
    </section>
  );
}
