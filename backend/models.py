"""
Shared data models for the pipeline.
Every model extractor must return data in this exact shape so the
frontend, evaluator, and Zoho pusher can all treat them identically.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class ExtractedBill(BaseModel):
    vendor_name: Optional[str] = None
    bill_date: Optional[str] = None          # ISO format YYYY-MM-DD if resolvable
    invoice_number: Optional[str] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    tax_rate_percent: Optional[float] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = "INR"
    payment_mode: Optional[str] = None       # cash / card / upi / unknown
    category_guess: Optional[str] = None     # e.g. "Travel", "Office Supplies"
    line_items: List[LineItem] = Field(default_factory=list)
    raw_model_notes: Optional[str] = None    # anything the model flagged as unclear

    # Meta (filled in by the pipeline, not the model)
    model_name: Optional[str] = None
    latency_seconds: Optional[float] = None
    estimated_cost_inr: Optional[float] = None
    error: Optional[str] = None


EXTRACTION_PROMPT = """You are an expert at reading handwritten and printed Indian retail bills/receipts.
Look at the attached bill image carefully. Handwriting may be messy, amounts may be in Rupees (₹ or Rs.),
and dates may be in DD/MM/YYYY or DD-MM-YY format.

Extract the following fields and return ONLY a single valid JSON object (no markdown fences, no commentary)
matching exactly this schema:

{
  "vendor_name": string or null,
  "bill_date": string or null (convert to YYYY-MM-DD if you can confidently determine it, else null),
  "invoice_number": string or null,
  "subtotal": number or null,
  "tax_amount": number or null,
  "tax_rate_percent": number or null,
  "total_amount": number or null,
  "currency": "INR",
  "payment_mode": string or null,
  "category_guess": string or null,
  "line_items": [ { "description": string, "quantity": number, "unit_price": number, "amount": number } ],
  "raw_model_notes": string or null (mention anything illegible or uncertain)
}

Rules:
- If a field is not present or illegible, use null. Do NOT guess numbers.
- total_amount should be the final payable amount on the bill.
- Do not wrap the JSON in ```json fences.
"""
