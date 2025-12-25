# processed_store.py

from typing import Set
from sheets_write import get_sheets_service, SPREADSHEET_ID

PROCESSED_SHEET_NAME = "processed_ids"
PROCESSED_RANGE = f"{PROCESSED_SHEET_NAME}!A2:A"


def load_processed_ids() -> Set[str]:
    """
    Load processed Gmail message IDs from the 'processed_ids' sheet.
    Returns a set of message_id strings.
    """
    service = get_sheets_service()
    sheet = service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=PROCESSED_RANGE,
    ).execute()

    values = result.get("values", [])
    ids: Set[str] = set()

    for row in values:
        if not row:
            continue
        msg_id = row[0].strip()
        if msg_id:
            ids.add(msg_id)

    print(
        f"[processed_store] Loaded {len(ids)} processed IDs from Google Sheet.",
        flush=True,
    )
    return ids


def save_processed_ids(processed_ids: Set[str]) -> None:
    """
    Persist processed Gmail message IDs to the 'processed_ids' sheet.

    Behavior:
    - Read existing IDs from the sheet.
    - Compute which IDs are new (present in processed_ids but not in the sheet).
    - Append only new IDs to the sheet.
    """
    if not processed_ids:
        print("[processed_store] No processed IDs to save.", flush=True)
        return

    service = get_sheets_service()
    sheet = service.spreadsheets()

    # Read existing IDs from the sheet
    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=PROCESSED_RANGE,
    ).execute()
    values = result.get("values", [])
    existing_ids: Set[str] = set()

    for row in values:
        if not row:
            continue
        msg_id = row[0].strip()
        if msg_id:
            existing_ids.add(msg_id)

    new_ids = processed_ids - existing_ids
    if not new_ids:
        print(
            "[processed_store] No NEW processed IDs to save "
            "(all already in sheet).",
            flush=True,
        )
        return

    # Append new IDs to column A
    body = {
        "values": [[msg_id] for msg_id in sorted(new_ids)]
    }

    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=PROCESSED_RANGE,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()

    print(
        f"[processed_store] Appended {len(new_ids)} new processed IDs "
        f"to Google Sheet.",
        flush=True,
    )
