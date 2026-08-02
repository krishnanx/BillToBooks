const FIELDS = [
  ["vendor_name", "Vendor"],
  ["bill_date", "Date"],
  ["invoice_number", "Invoice #"],
  ["subtotal", "Subtotal"],
  ["tax_amount", "Tax"],
  ["total_amount", "Total"],
  ["payment_mode", "Payment mode"],
  ["category_guess", "Category"],
  ["latency_seconds", "Latency (s)"],
  ["estimated_cost_inr", "Est. cost (₹)"],
];

export default function ResultsLedger({ results, onUseModel }) {
  if (!results) return null;
  const models = Object.keys(results);

  return (
    <section className="sheet">
      <div className="sheet-tab">02</div>
      <h2>Compare extractions</h2>

      <div className="ledger-scroll">
        <table className="ledger">
          <thead>
            <tr>
              <th>Field</th>
              {models.map((m) => (
                <th key={m}>
                  {m}
                  {results[m].error && <span className="badge badge-err">error</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FIELDS.map(([key, label]) => (
              <tr key={key}>
                <td className="ledger-label">{label}</td>
                {models.map((m) => (
                  <td key={m} className="mono">
                    {results[m][key] ?? "—"}
                  </td>
                ))}
              </tr>
            ))}
            {results[models[0]]?.raw_model_notes !== undefined && (
              <tr>
                <td className="ledger-label">Notes</td>
                {models.map((m) => (
                  <td key={m}>{results[m].raw_model_notes || "—"}</td>
                ))}
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="action-row">
        {models.map((m) => (
          <button
            key={m}
            className="btn-outline"
            disabled={!!results[m].error}
            onClick={() => onUseModel(m)}
          >
            Use {m} for Zoho push
          </button>
        ))}
      </div>
    </section>
  );
}
