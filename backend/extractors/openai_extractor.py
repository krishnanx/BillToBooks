import os
import httpx
from backend.models import EXTRACTION_PROMPT, ExtractedBill
from backend.extractors.base import encode_image, parse_json_response, TimedExtraction

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

PRICE_INPUT_PER_1K_INR = float(os.getenv("OPENAI_PRICE_INPUT_PER_1K_INR", "0.0125"))
PRICE_OUTPUT_PER_1K_INR = float(os.getenv("OPENAI_PRICE_OUTPUT_PER_1K_INR", "0.05"))


async def extract_with_openai(image_path_or_bytes) -> ExtractedBill:
    timer = TimedExtraction(f"openai:{OPENAI_MODEL}")
    if not OPENAI_API_KEY:
        return timer.fail("OPENAI_API_KEY not set")

    b64, mime = encode_image(image_path_or_bytes)
    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": EXTRACTION_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(OPENAI_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        cost = (in_tok / 1000) * PRICE_INPUT_PER_1K_INR + (out_tok / 1000) * PRICE_OUTPUT_PER_1K_INR
        parsed = parse_json_response(text)
        return timer.finish(parsed, cost)
    except Exception as e:
        return timer.fail(str(e))
