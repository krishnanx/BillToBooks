import base64
import json
import re
import time
import mimetypes
from backend.models import ExtractedBill


def encode_image(path_or_bytes) -> tuple[str, str]:
    """Returns (base64_string, mime_type) for a file path or raw bytes."""
    if isinstance(path_or_bytes, (bytes, bytearray)):
        data = path_or_bytes
        mime = "image/jpeg"
    else:
        with open(path_or_bytes, "rb") as f:
            data = f.read()
        mime = mimetypes.guess_type(str(path_or_bytes))[0] or "image/jpeg"
    return base64.b64encode(data).decode("utf-8"), mime


def parse_json_response(text: str) -> dict:
    """Models sometimes wrap JSON in ```json fences or add stray text. Strip and parse."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    # If there's leading/trailing chatter, grab the outermost { ... }
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
    return json.loads(text)


class TimedExtraction:
    """Context manager to measure latency and wrap errors into ExtractedBill."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.start = None
        self.result: ExtractedBill | None = None

    def __enter__(self):
        self.start = time.time()
        return self

    def finish(self, data: dict, cost_inr: float = 0.0) -> ExtractedBill:
        elapsed = time.time() - self.start
        bill = ExtractedBill(**data)
        bill.model_name = self.model_name
        bill.latency_seconds = round(elapsed, 2)
        bill.estimated_cost_inr = round(cost_inr, 4)
        self.result = bill
        return bill

    def fail(self, error_msg: str) -> ExtractedBill:
        elapsed = time.time() - self.start
        bill = ExtractedBill(model_name=self.model_name, latency_seconds=round(elapsed, 2), error=error_msg)
        self.result = bill
        return bill
