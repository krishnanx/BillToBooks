"""
Minimal Zoho Books client.

Setup required (see README section "Zoho Books setup"):
  1. Create a Self Client in the Zoho API Console -> get CLIENT_ID / CLIENT_SECRET
  2. Generate a one-time grant token with scope ZohoBooks.fullaccess.all
  3. Exchange it for a REFRESH_TOKEN (one-time, see README) and store it in .env
  4. Put your Organization ID (Zoho Books -> Settings -> Organizations) in .env
  5. Put a valid expense ACCOUNT_ID (chart of accounts, e.g. "Office Supplies")
     in .env - Zoho Books requires every expense to post against an account.

Region note: Indian Zoho accounts use the .in domain. If your org is on a
different Zoho data centre, change ZOHO_ACCOUNTS_BASE / ZOHO_API_BASE below.
"""
import os
import time
import httpx

ZOHO_ACCOUNTS_BASE = os.getenv("ZOHO_ACCOUNTS_BASE", "https://accounts.zoho.in")
ZOHO_API_BASE = os.getenv("ZOHO_API_BASE", "https://www.zohoapis.in/books/v3")

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET", "")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN", "")
ORG_ID = os.getenv("ZOHO_ORGANIZATION_ID", "")
DEFAULT_ACCOUNT_ID = os.getenv("ZOHO_EXPENSE_ACCOUNT_ID", "")

_token_cache = {"access_token": None, "expires_at": 0}


async def _get_access_token() -> str:
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["access_token"]

    if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
        raise RuntimeError("Zoho OAuth env vars missing (ZOHO_CLIENT_ID/SECRET/REFRESH_TOKEN)")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{ZOHO_ACCOUNTS_BASE}/oauth/v2/token", params={
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
        })
    resp.raise_for_status()
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"Zoho token refresh failed: {data}")
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
    return _token_cache["access_token"]


async def _headers() -> dict:
    token = await _get_access_token()
    return {"Authorization": f"Zoho-oauthtoken {token}"}


async def find_or_create_vendor(vendor_name: str) -> str:
    """Returns a contact_id for the vendor, creating it in Zoho Books if needed."""
    if not vendor_name:
        vendor_name = "Unknown Vendor"

    headers = await _headers()
    async with httpx.AsyncClient(timeout=30) as client:
        search = await client.get(
            f"{ZOHO_API_BASE}/contacts",
            headers=headers,
            params={"organization_id": ORG_ID, "contact_name": vendor_name},
        )
        search.raise_for_status()
        results = search.json().get("contacts", [])
        for c in results:
            if c.get("contact_name", "").strip().lower() == vendor_name.strip().lower():
                return c["contact_id"]

        create = await client.post(
            f"{ZOHO_API_BASE}/contacts",
            headers=headers,
            params={"organization_id": ORG_ID},
            json={"contact_name": vendor_name, "contact_type": "vendor"},
        )
        create.raise_for_status()
        return create.json()["contact"]["contact_id"]


async def push_expense(bill, image_bytes: bytes | None = None, filename: str = "receipt.jpg") -> dict:
    """
    bill: an ExtractedBill (see backend/models.py)
    Creates an Expense record in Zoho Books and optionally attaches the
    original receipt image as a scanned copy.
    """
    if not ORG_ID:
        raise RuntimeError("ZOHO_ORGANIZATION_ID not set")
    if not DEFAULT_ACCOUNT_ID:
        raise RuntimeError("ZOHO_EXPENSE_ACCOUNT_ID not set - pick an account in Zoho Books > Accountant > Chart of Accounts")

    vendor_id = await find_or_create_vendor(bill.vendor_name)
    headers = await _headers()

    expense_payload = {
        "account_id": DEFAULT_ACCOUNT_ID,
        "date": bill.bill_date or time.strftime("%Y-%m-%d"),
        "amount": bill.total_amount or 0,
        "vendor_id": vendor_id,
        "reference_number": bill.invoice_number or "",
        "description": f"Auto-extracted by {bill.model_name}. Notes: {bill.raw_model_notes or 'none'}",
        "is_inclusive_tax": True,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{ZOHO_API_BASE}/expenses",
            headers=headers,
            params={"organization_id": ORG_ID},
            json=expense_payload,
        )
        resp.raise_for_status()
        result = resp.json()
        expense_id = result["expense"]["expense_id"]

        if image_bytes:
            files = {"receipt": (filename, image_bytes, "image/jpeg")}
            attach = await client.post(
                f"{ZOHO_API_BASE}/expenses/{expense_id}/receipt",
                headers=headers,
                params={"organization_id": ORG_ID},
                files=files,
            )
            # Non-fatal if attachment fails - the expense itself is already created.
            result["receipt_attached"] = attach.status_code == 200

    return result
