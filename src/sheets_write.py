from typing import List, Dict
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE"  # <-- user replaces this
RANGE_NAME = "Sheet1!A2:O"  # Adjust range as needed
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheets_service():
    if not SPREADSHEET_ID:
        raise RuntimeError(
            "SPREADSHEET_ID is not set. "
            "Please set it to your Google Sheet ID."
        )
    creds = Credentials.from_service_account_file(
        "service_account.json", scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)
    return service


def append_items_to_sheet(items: List[Dict]):
    """Append a list of item dicts to the Google Sheet."""
    if not items:
        return
    service = get_sheets_service()
    values = [
        [
            item.get("product_name", ""),
            item.get("category", ""),
            item.get("subcategory", ""),
            item.get("vendor", ""),
            item.get("manufacturer_part_number", ""),
            item.get("quantity", ""),
            item.get("unit_price", ""),
            item.get("total_price", ""),
            item.get("funding_source", ""),
            item.get("requester", ""),
            item.get("pi_name", ""),
            item.get("order_date", ""),
            item.get("expiration_date", ""),
            item.get("billing_cycle", ""),
            item.get("location_or_owner", ""),
        ]
        for item in items
    ]
    body = {"values": values}
    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()