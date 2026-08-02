import os
import httpx
from backend.models import EXTRACTION_PROMPT, ExtractedBill
from backend.extractors.base import encode_image, parse_json_response, TimedExtraction

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# IMPORTANT: verify the exact current model slug in your Anthropic Console
# (Settings -> Models) before running - naming changes over time.
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

PRICE_INPUT_PER_1K_INR = float(os.getenv("CLAUDE_PRICE_INPUT_PER_1K_INR", "0.068"))
PRICE_OUTPUT_PER_1K_INR = float(os.getenv("CLAUDE_PRICE_OUTPUT_PER_1K_INR", "0.34"))


async def extract_with_claude(image_path_or_bytes) -> ExtractedBill:
    timer = TimedExtraction(f"claude:{CLAUDE_MODEL}")
    if not ANTHROPIC_API_KEY:
        return timer.fail("ANTHROPIC_API_KEY not set")

    b64, mime = encode_image(image_path_or_bytes)
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1024,
        "temperature": 0,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                {"type": "text", "text": EXTRACTION_PROMPT},
            ],
        }],
    }
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(ANTHROPIC_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        usage = data.get("usage", {})
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        cost = (in_tok / 1000) * PRICE_INPUT_PER_1K_INR + (out_tok / 1000) * PRICE_OUTPUT_PER_1K_INR
        parsed = parse_json_response(text)
        return timer.finish(parsed, cost)
    except Exception as e:
        return timer.fail(str(e))
