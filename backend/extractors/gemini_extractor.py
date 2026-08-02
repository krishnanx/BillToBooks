import os
import httpx
from backend.models import EXTRACTION_PROMPT, ExtractedBill
from backend.extractors.base import encode_image, parse_json_response, TimedExtraction

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# Rough published per-1K-token pricing placeholders (INR). Update in .env-driven config
# if you want exact cost tracking; these are only used for the comparison table.
PRICE_INPUT_PER_1K_INR = float(os.getenv("GEMINI_PRICE_INPUT_PER_1K_INR", "0.026"))
PRICE_OUTPUT_PER_1K_INR = float(os.getenv("GEMINI_PRICE_OUTPUT_PER_1K_INR", "0.104"))


async def extract_with_gemini(image_path_or_bytes) -> ExtractedBill:
    timer = TimedExtraction(f"gemini:{GEMINI_MODEL}")
    if not GEMINI_API_KEY:
        return timer.fail("GEMINI_API_KEY not set")

    b64, mime = encode_image(image_path_or_bytes)
    payload = {
        "contents": [{
            "parts": [
                {"text": EXTRACTION_PROMPT},
                {"inline_data": {"mime_type": mime, "data": b64}}
            ]
        }],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0}
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                GEMINI_URL, params={"key": GEMINI_API_KEY}, json=payload
            )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        in_tok = usage.get("promptTokenCount", 0)
        out_tok = usage.get("candidatesTokenCount", 0)
        cost = (in_tok / 1000) * PRICE_INPUT_PER_1K_INR + (out_tok / 1000) * PRICE_OUTPUT_PER_1K_INR
        parsed = parse_json_response(text)
        return timer.finish(parsed, cost)
    except Exception as e:
        return timer.fail(str(e))
