const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function extractBill(file, models) {
  const form = new FormData();
  form.append("file", file);
  form.append("models", models.join(","));
  const res = await fetch(`${API_BASE}/extract`, { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Extraction failed");
  return data;
}

export async function pushToZoho(file, fields) {
  const form = new FormData();
  form.append("file", file);
  Object.entries(fields).forEach(([k, v]) => form.append(k, v ?? ""));
  const res = await fetch(`${API_BASE}/push-to-zoho`, { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Push to Zoho failed");
  return data;
}
