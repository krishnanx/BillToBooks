# BillToBooks

Handwritten receipts, read by AI, entered into Zoho Books.

Extracts structured data (vendor, date, amount, tax, line items) from photos of
handwritten Indian bills/receipts using 2-3 vision LLMs, lets you compare their
output side by side, and pushes the corrected result into Zoho Books as an
Expense via the Zoho Books API.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + Vite (plain CSS, no UI framework) |
| Backend | Python + FastAPI (async) |
| Vision LLMs | Google Gemini API, Anthropic Claude API, OpenAI API (optional 3rd) |
| Accounting integration | Zoho Books REST API (OAuth2 refresh-token flow) |
| HTTP client (backend → LLM/Zoho APIs) | httpx (async) |
| Evaluation | Python script (csv/pandas) scoring field accuracy, latency, cost |

## Architecture

```
frontend/index.html  --(upload image, pick models)-->  backend (FastAPI)
                                                            |
                                          ┌─────────────────┼─────────────────┐
                                   Gemini API         Anthropic API       OpenAI API
                                   (Google AI Studio) (Claude)            (optional 3rd)
                                                            |
                                             merged JSON results returned to UI
                                                            |
                                        user reviews / edits, clicks "Push to Zoho"
                                                            |
                                              Zoho Books API (OAuth refresh token)
                                              -> finds/creates Vendor contact
                                              -> creates Expense record
                                              -> attaches original receipt image
```

Backend: **FastAPI** (Python, async), no framework lock-in, one route per concern.
Frontend: **React 18 + Vite**, plain CSS (no component library) - a three-step
review flow (upload → compare models → edit & push to Zoho).
Evaluation: a standalone script that runs every configured model against a small
hand-labelled sample set and reports field-level accuracy, latency, and cost.

## Repo layout

```
backend/
  main.py                 FastAPI app: /extract and /push-to-zoho
  models.py                Shared ExtractedBill schema + the extraction prompt
  extractors/
    gemini_extractor.py    Google AI Studio (Gemini) vision call
    claude_extractor.py    Anthropic Claude vision call
    openai_extractor.py    OpenAI GPT-4o-mini vision call (optional 3rd model)
  zoho/
    zoho_client.py         OAuth token refresh, vendor find/create, expense push
  .env.example             Copy to backend/.env and fill in your keys
  requirements.txt
frontend/                  React + Vite app
  src/
    App.jsx                 Top-level state: upload -> extract -> compare -> push
    App.css / index.css     Styling (ledger/receipt-themed design tokens)
    api.js                   fetch() wrappers for the FastAPI backend
    components/
      UploadPanel.jsx        Step 1: image upload + model selection
      ResultsLedger.jsx      Step 2: side-by-side model comparison table
      PushPanel.jsx           Step 3: editable fields + push to Zoho Books
  index.html, vite.config.js, package.json
  .env.example              Copy to .env - points the app at your backend URL
evaluation/
  ground_truth.csv         You fill this in by hand for your sample bills
  sample_bills/            Put 5-10 real handwritten bill photos here
  evaluate.py              Runs all models, scores against ground_truth.csv
  results_summary.csv      Generated after you run evaluate.py
```

---

## What YOU need to set up (nothing here needs "their" codebase)

### 1. Get 2 (or 3) vision LLM API keys

You said you have **Gemini Pro** — that covers one model for free/cheap. Pick one
more from a free trial so you have a genuine comparison:

| Provider | Where to get a key | Notes |
|---|---|---|
| **Google AI Studio (Gemini)** | https://aistudio.google.com/app/apikey | Your Pro plan covers this. Copy the key into `GEMINI_API_KEY`. |
| **Anthropic Console (Claude)** | https://console.anthropic.com/ | New accounts get free trial credits. Create an API key, copy into `ANTHROPIC_API_KEY`. **Check the exact model name shown in Console → Models** and set `CLAUDE_MODEL` in `.env` to match — model slugs change over time and the one in the code is only a sensible default. |
| **OpenAI (optional 3rd)** | https://platform.openai.com/api-keys | Optional. New accounts sometimes get trial credit; if not, skip this model and just compare Gemini vs Claude — the assignment only requires 2-3. |

Only fill in the keys for the models you're actually comparing; leave the others
blank in `.env` and the pipeline will simply skip them.

### 2. Set up Zoho Books (free plan is fine)

1. Sign up for **Zoho Books Free plan**: https://www.zoho.com/in/books/signup/
2. Note your **Organization ID**: Zoho Books → Settings (gear icon) → Organizations → copy the numeric ID.
3. Note an **Expense Account ID**: Zoho Books → Accountant → Chart of Accounts → open any expense-type account (e.g. "Office Supplies") — its ID is in the URL, or fetch it via `GET /chartofaccounts` once you have an access token. Put it in `ZOHO_EXPENSE_ACCOUNT_ID`.
4. Register a **Self Client** to get API credentials:
   - Go to https://api-console.zoho.in/ (use `.in` since you're in India) → **Add Client** → **Self Client**.
   - This gives you a `Client ID` and `Client Secret` → put into `ZOHO_CLIENT_ID` / `ZOHO_CLIENT_SECRET`.
5. Generate a **grant token** (one-time, valid ~10 minutes) from the same Self Client screen:
   - Scope: `ZohoBooks.fullaccess.all`
   - Time duration: 10 minutes, redirect URL: anything (e.g. `https://www.zoho.com`)
   - Click Create → copy the generated code.
6. Exchange that grant code for a **refresh token** (do this once, from your terminal):
   ```bash
   curl -X POST https://accounts.zoho.in/oauth/v2/token \
     -d "grant_type=authorization_code" \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET" \
     -d "redirect_uri=https://www.zoho.com" \
     -d "code=THE_GRANT_CODE_YOU_COPIED"
   ```
   The response JSON contains `refresh_token` — put that into `ZOHO_REFRESH_TOKEN`.
   This refresh token doesn't expire (unless revoked), so you only do this once.

### 3. Collect 5-10 handwritten bill photos

The whole point of the assignment is **handwritten** Indian bills, so:
- Photograph a few real receipts (kirana store, auto-rickshaw, chemist, tea stall, etc.) with your phone, in reasonable light.
- Drop them into `evaluation/sample_bills/` as `bill_01.jpg`, `bill_02.jpg`, ...
- Manually read each bill and fill in the true values in `evaluation/ground_truth.csv` (vendor, date, total, tax, invoice number). This is your ground truth for scoring the models — it must be typed by a human, not by a model, or the evaluation is circular.

### 4. Install and run

```bash
# Backend
cd handwritten-bill-pipeline
cp backend/.env.example backend/.env      # then fill in your keys
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000

# Frontend (in another terminal)
cd frontend
cp .env.example .env          # points the app at http://localhost:8000 by default
npm install
npm run dev
# open http://localhost:5500 in your browser
```

### 5. Run the evaluation

```bash
python -m evaluation.evaluate
```

This produces `evaluation/results_summary.csv` and prints a markdown table —
paste that table into the **Accuracy & cost comparison** section below.

---

## Evaluation methodology

- **Dataset**: 5-10 real handwritten Indian bills, hand-transcribed into `ground_truth.csv` by a human (not by any model) to avoid circular grading.
- **Fields graded**: `vendor_name`, `bill_date`, `total_amount`, `tax_amount`, `invoice_number` — the fields with an objective, checkable ground truth. Line items and category guesses are inspected manually but not auto-scored since they're subjective/free-form.
- **Matching rule**: strings are compared case-insensitively after trimming; monetary fields allow a ₹0.50 tolerance for rounding. A field only counts toward accuracy if the ground truth actually has a value for it (blank ground-truth cells are skipped, not counted as failures).
- **Metrics captured per model**: field-level accuracy %, average latency per bill, average estimated cost per bill (from each API's reported token usage × published per-token pricing), and hard failure rate (API errors / malformed JSON).
- **Why this over exact-JSON-match**: bills are messy and models phrase things slightly differently (e.g. "M/S Sharma Traders" vs "Sharma Traders"); field-level fuzzy matching reflects real usefulness better than requiring byte-identical output.

## Accuracy & cost comparison

Run `python -m evaluation.evaluate` and paste the printed table here, e.g.:

| Model | Field Accuracy | Avg Latency (s) | Avg Cost/Bill (INR) | Errors |
|---|---|---|---|---|
| gemini | — | — | — | — |
| claude | — | — | — | — |
| openai | — | — | — | — |

*(Numbers are intentionally left blank here — they depend on your specific
sample bills and current API pricing, and should come from your own run of
`evaluate.py`, not be assumed.)*

Qualitative notes worth adding once you've looked at `results_raw.csv`:
- Which model handled messy/cursive handwriting better?
- Which model was more likely to hallucinate a number vs. correctly return `null` for illegible fields?
- Did any model consistently misparse DD/MM/YYYY dates as MM/DD/YYYY?

## Final recommendation

Fill this in after running the evaluation — a good recommendation is one line
of trade-off, e.g.:

> "Gemini 2.5 Flash gave the best accuracy-per-rupee for this sample and is
> already covered by an existing Pro plan, so it's the primary extractor;
> Claude is kept as a secondary check on the ~15% of bills where the model
> returns `raw_model_notes` flagging low confidence, since a second opinion
> on ambiguous handwriting is cheap relative to a bad expense entry going
> into the books unnoticed."

Justify your recommendation against **all three metrics** (accuracy, latency,
cost) rather than accuracy alone — for a bookkeeping pipeline, a model that's
95% accurate but costs 10x more per bill isn't obviously better than one at 90%
that's near-free, especially if a human reviews the extracted fields before
pushing to Zoho Books anyway (which this UI is designed to require).

## Known limitations / scope notes

- Tax handling in Zoho Books normally requires a `tax_id` reference rather than
  a raw percentage; this pipeline stores the extracted tax amount in the
  expense description/amount but does not attempt to map it to a specific Zoho
  tax rate object, since that mapping is organization-specific.
- Vendor matching is exact-name lookup with auto-create-if-missing; it doesn't
  do fuzzy vendor deduplication (e.g. "Sharma Traders" vs "M/S Sharma Traders"
  would create two contacts). A production version would add a fuzzy-match or
  a manual "link to existing vendor" step.
- The frontend intentionally requires a human-in-the-loop review step before
  anything is pushed to Zoho Books — auto-pushing unreviewed OCR output into
  accounting records is not something this pipeline does by design.
