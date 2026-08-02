"""
Run this after you've:
  1. Dropped 5-10 real handwritten bill photos into evaluation/sample_bills/
  2. Filled in evaluation/ground_truth.csv by hand for those same files
  3. Filled backend/.env with your API keys

Usage:
    cd handwritten-bill-pipeline
    python -m evaluation.evaluate

Produces:
    evaluation/results_raw.csv     -> every model's raw output per bill
    evaluation/results_summary.csv -> per-model field accuracy + avg latency + avg cost
    Prints a markdown table you can paste straight into the README.
"""
import asyncio
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / "backend" / ".env")

from backend.extractors.gemini_extractor import extract_with_gemini
from backend.extractors.claude_extractor import extract_with_claude
from backend.extractors.openai_extractor import extract_with_openai

HERE = Path(__file__).resolve().parent
SAMPLE_DIR = HERE / "sample_bills"
GT_PATH = HERE / "ground_truth.csv"

MODELS = {
    "gemini": extract_with_gemini,
    "claude": extract_with_claude,
    "openai": extract_with_openai,
}

# Only fields we can objectively grade against ground truth
COMPARE_FIELDS = ["vendor_name", "bill_date", "total_amount", "tax_amount", "invoice_number"]


def load_ground_truth():
    gt = {}
    with open(GT_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["filename"].strip():
                gt[row["filename"].strip()] = row
    return gt


def fields_match(predicted, expected, field) -> bool:
    if expected in (None, ""):
        return True  # nothing to grade against for this field
    if predicted is None:
        return False
    if field in ("total_amount", "tax_amount"):
        try:
            return abs(float(predicted) - float(expected)) < 0.5  # tolerate rounding
        except (ValueError, TypeError):
            return False
    return str(predicted).strip().lower() == str(expected).strip().lower()


async def run():
    gt = load_ground_truth()
    if not gt:
        print(f"No ground truth rows found in {GT_PATH}. Fill it in first.")
        return

    active_models = {name: fn for name, fn in MODELS.items() if os.getenv(f"{name.upper()}_API_KEY")}
    if not active_models:
        print("No API keys found in backend/.env - set at least 2 of GEMINI_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY")
        return
    print(f"Evaluating models: {list(active_models)}")

    raw_rows = []
    scores = {name: {f: [0, 0] for f in COMPARE_FIELDS} for name in active_models}  # [correct, total]
    latencies = {name: [] for name in active_models}
    costs = {name: [] for name in active_models}
    errors = {name: 0 for name in active_models}

    for filename, expected in gt.items():
        img_path = SAMPLE_DIR / filename
        if not img_path.exists():
            print(f"  [skip] {filename} not found in sample_bills/")
            continue
        print(f"Processing {filename} ...")

        for name, extractor_fn in active_models.items():
            bill = await extractor_fn(img_path)
            row = {"filename": filename, "model": name, **bill.model_dump()}
            raw_rows.append(row)

            if bill.error:
                errors[name] += 1
                continue

            latencies[name].append(bill.latency_seconds or 0)
            costs[name].append(bill.estimated_cost_inr or 0)

            for field in COMPARE_FIELDS:
                exp_val = expected.get(field, "")
                predicted = getattr(bill, field, None)
                correct = fields_match(predicted, exp_val, field)
                if exp_val not in (None, ""):
                    scores[name][field][1] += 1
                    if correct:
                        scores[name][field][0] += 1

    # --- write raw results ---
    if raw_rows:
        with open(HERE / "results_raw.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(raw_rows[0].keys()))
            writer.writeheader()
            writer.writerows(raw_rows)

    # --- build summary ---
    summary_rows = []
    print("\n\n| Model | Field Accuracy | Avg Latency (s) | Avg Cost/Bill (INR) | Errors |")
    print("|---|---|---|---|---|")
    for name in active_models:
        correct_total = sum(c for c, t in scores[name].values())
        graded_total = sum(t for c, t in scores[name].values())
        acc = (correct_total / graded_total * 100) if graded_total else 0
        avg_lat = sum(latencies[name]) / len(latencies[name]) if latencies[name] else 0
        avg_cost = sum(costs[name]) / len(costs[name]) if costs[name] else 0
        print(f"| {name} | {acc:.1f}% | {avg_lat:.2f} | {avg_cost:.4f} | {errors[name]} |")
        summary_rows.append({
            "model": name, "field_accuracy_pct": round(acc, 1),
            "avg_latency_sec": round(avg_lat, 2), "avg_cost_inr": round(avg_cost, 4),
            "errors": errors[name],
        })

    with open(HERE / "results_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote {HERE / 'results_raw.csv'} and {HERE / 'results_summary.csv'}")


if __name__ == "__main__":
    asyncio.run(run())
