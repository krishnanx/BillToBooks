export default function PushPanel({ fields, onChange, onPush, pushing, pushResult }) {
  if (!fields) return null;

  const update = (key) => (e) => onChange({ ...fields, [key]: e.target.value });

  return (
    <section className="sheet">
      <div className="sheet-tab">03</div>
      <h2>Review &amp; push to Zoho Books</h2>
      <p className="hint">Correct anything the model got wrong before it enters the books.</p>

      <div className="form-grid">
        <label>
          Vendor name
          <input value={fields.vendor_name} onChange={update("vendor_name")} />
        </label>
        <label>
          Bill date
          <input value={fields.bill_date} onChange={update("bill_date")} placeholder="YYYY-MM-DD" />
        </label>
        <label>
          Total amount (₹)
          <input value={fields.total_amount} onChange={update("total_amount")} type="number" step="0.01" />
        </label>
        <label>
          Invoice number
          <input value={fields.invoice_number} onChange={update("invoice_number")} />
        </label>
      </div>

      <div className="action-row">
        <button className="btn-stamp" onClick={onPush} disabled={pushing}>
          {pushing ? "Pushing…" : "Push to Zoho Books"}
        </button>
        {pushResult && (
          <span className={`badge ${pushResult.ok ? "badge-ok" : "badge-err"}`}>
            {pushResult.message}
          </span>
        )}
      </div>
    </section>
  );
}
