import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from backend.extractors.gemini_extractor import extract_with_gemini
from backend.extractors.claude_extractor import extract_with_claude
from backend.extractors.openai_extractor import extract_with_openai
from backend.zoho import zoho_client

app = FastAPI(title="Handwritten Bill Extraction Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for a local assignment demo (covers the Vite dev server on :5500); tighten for real deployments
    allow_methods=["*"],
    allow_headers=["*"],
)

EXTRACTOR_MAP = {
    "gemini": extract_with_gemini,
    "claude": extract_with_claude,
    "openai": extract_with_openai,
}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/extract")
async def extract(
    file: UploadFile = File(...),
    models: str = Form("gemini,claude"),  # comma-separated: gemini,claude,openai
):
    """Runs the chosen vision models on one bill image and returns all results side by side."""
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(400, "Empty file")

    requested = [m.strip() for m in models.split(",") if m.strip() in EXTRACTOR_MAP]
    if not requested:
        raise HTTPException(400, f"No valid models requested. Choose from {list(EXTRACTOR_MAP)}")

    results = {}
    for m in requested:
        bill = await EXTRACTOR_MAP[m](image_bytes)
        results[m] = bill.model_dump()

    return {"filename": file.filename, "results": results}


@app.post("/push-to-zoho")
async def push_to_zoho(
    file: UploadFile = File(...),
    vendor_name: str = Form(...),
    bill_date: str = Form(...),
    total_amount: float = Form(...),
    invoice_number: str = Form(""),
    model_name: str = Form("manual"),
    raw_model_notes: str = Form(""),
):
    """Pushes a (possibly human-corrected) extracted bill into Zoho Books as an Expense."""
    image_bytes = await file.read()

    class Bill:  # lightweight shim, avoids re-importing pydantic model here
        pass
    bill = Bill()
    bill.vendor_name = vendor_name
    bill.bill_date = bill_date
    bill.total_amount = total_amount
    bill.invoice_number = invoice_number
    bill.model_name = model_name
    bill.raw_model_notes = raw_model_notes

    try:
        result = await zoho_client.push_expense(bill, image_bytes, file.filename or "receipt.jpg")
        return {"success": True, "zoho_response": result}
    except Exception as e:
        raise HTTPException(500, f"Zoho push failed: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
