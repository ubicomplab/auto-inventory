import time
from typing import Set

from sheets_write import append_items_to_sheet
from gmail_fetch import fetch_order_emails
from inventory_pipeline import extract_inventory_items
from processed_store import load_processed_ids, save_processed_ids

SLEEP_SECONDS = 5 * 60 * 60 # 5 hours

print("=== START pipeline ===", flush=True)

def run_pipeline_once(processed_ids: Set[str]) -> None:
    """Run one full pipeline: fetch -> LLM -> write to Google Sheet."""
    print("Fetching emails...", flush=True)
    emails = fetch_order_emails(max_results=50)
    print(f"Fetched {len(emails)} emails (before filtering processed ones)", flush=True)
    all_items = []
    new_ids: Set[str] = set()
    for msg in emails:
        msg_id = msg.get("id")
        if not msg_id:
            continue
        if msg_id in processed_ids:
            continue
        body = msg.get("body", "") or ""
        pdf_attachments = msg.get("pdf_attachments", []) or []
        # Skip emails that have neither text body nor PDF attachments
        if not body and not pdf_attachments:
            continue
        try:
            print(
                f"Processing email id={msg_id} subject={msg.get('subject')}",
                flush=True,
            )
            # Pass both body and pdf_attachments to the LLM
            items = extract_inventory_items(body, pdf_attachments)
            if isinstance(items, list):
                all_items.extend(items)
                new_ids.add(msg_id)
            else:
                print("LLM returned non-list result, skipping.", flush=True)
        except Exception as e:
            print(f"Error processing email {msg_id}: {e}", flush=True)
    if all_items:
        print(f"Writing {len(all_items)} items to Google Sheet...", flush=True)
        append_items_to_sheet(all_items)
        processed_ids.update(new_ids)
        save_processed_ids(processed_ids)
        print(f"Saved {len(processed_ids)} processed IDs.", flush=True)
    else:
        print("No new items extracted in this cycle.", flush=True)
    print("Pipeline run finished.", flush=True)


def main():
    processed_ids = load_processed_ids()
    print(f"Loaded {len(processed_ids)} processed IDs.", flush=True)
    while True:
        try:
            run_pipeline_once(processed_ids)
        except Exception as e:
            print(f"Fatal error in pipeline: {e}", flush=True)
        print(f"Sleeping {SLEEP_SECONDS} seconds before next run...", flush=True)
        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()

