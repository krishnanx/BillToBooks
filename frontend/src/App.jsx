import { useState } from "react";
import UploadPanel from "./components/UploadPanel.jsx";
import ResultsLedger from "./components/ResultsLedger.jsx";
import PushPanel from "./components/PushPanel.jsx";
import { extractBill, pushToZoho } from "./api.js";
import "./App.css";

export default function App() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [selectedModels, setSelectedModels] = useState(["gemini", "claude"]);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [results, setResults] = useState(null);

  const [pushFields, setPushFields] = useState(null);
  const [pushingModel, setPushingModel] = useState(null);
  const [pushing, setPushing] = useState(false);
  const [pushResult, setPushResult] = useState(null);

  const handleFile = (f) => {
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
    setResults(null);
    setPushFields(null);
    setPushResult(null);
  };

  const toggleModel = (id) => {
    setSelectedModels((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  const handleExtract = async () => {
    if (!file || selectedModels.length === 0) return;
    setLoading(true);
    setStatusText("Running models — this can take 5–20s each…");
    try {
      const data = await extractBill(file, selectedModels);
      setResults(data.results);
      setStatusText("Done.");
    } catch (err) {
      setStatusText(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUseModel = (modelKey) => {
    const r = results[modelKey];
    setPushingModel(modelKey);
    setPushFields({
      vendor_name: r.vendor_name || "",
      bill_date: r.bill_date || "",
      total_amount: r.total_amount ?? "",
      invoice_number: r.invoice_number || "",
    });
    setPushResult(null);
  };

  const handlePush = async () => {
    setPushing(true);
    setPushResult(null);
    try {
      const data = await pushToZoho(file, {
        ...pushFields,
        model_name: pushingModel,
        raw_model_notes: results?.[pushingModel]?.raw_model_notes || "",
      });
      setPushResult({ ok: true, message: `Pushed — Expense ID ${data.zoho_response.expense.expense_id}` });
    } catch (err) {
      setPushResult({ ok: false, message: err.message });
    } finally {
      setPushing(false);
    }
  };

  return (
    <div className="page">
      <header className="masthead">
        <span className="masthead-mark">✎</span>
        <div>
          <h1>BillToBooks</h1>
          <p>Handwritten receipts, read by AI, entered into Zoho Books.</p>
        </div>
      </header>

      <main className="ledger-pad">
        <UploadPanel
          file={file}
          onFile={handleFile}
          previewUrl={previewUrl}
          selectedModels={selectedModels}
          onToggleModel={toggleModel}
          onExtract={handleExtract}
          loading={loading}
          statusText={statusText}
        />

        <ResultsLedger results={results} onUseModel={handleUseModel} />

        <PushPanel
          fields={pushFields}
          onChange={setPushFields}
          onPush={handlePush}
          pushing={pushing}
          pushResult={pushResult}
        />
      </main>
    </div>
  );
}
