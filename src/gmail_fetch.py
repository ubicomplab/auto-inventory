from __future__ import print_function
# import io
from typing import List, Dict
import os.path
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_gmail_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def collect_pdf_parts(payload) -> List[Dict]:
    """
    Recursively collect all parts that are PDF attachments.
    Returns a list of parts where each part has
    mimeType == 'application/pdf' and a non-empty filename.
    """
    pdf_parts: List[Dict] = []
    if "parts" in payload:
        for part in payload["parts"]:
            mime = part.get("mimeType", "")
            filename = part.get("filename", "")
            if mime == "application/pdf" and filename:
                pdf_parts.append(part)
            # Recurse into nested parts
            pdf_parts.extend(collect_pdf_parts(part))
    return pdf_parts

def get_message_body(payload):
    if "parts" in payload:
        for part in payload["parts"]:
            mime = part.get("mimeType", "")
            if mime == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data + "===").decode(
                        "utf-8", "ignore"
                    )
        for part in payload["parts"]:
            body = get_message_body(part)
            if body:
                return body
        return ""
    else:
        data = payload.get("body", {}).get("data")
        if not data:
            return ""
        return base64.urlsafe_b64decode(data + "===").decode("utf-8", "ignore")
    
def fetch_order_emails(
    max_results: int = 5,
    query: str | None = None,
):
    service = get_gmail_service()
    if query is None:
        query = '"Purchase" OR "order"'
    results = (
        service.users().messages().list(userId="me", maxResults=max_results, q=query).execute()
    )
    messages = results.get("messages", [])   
    emails: List[Dict] = []
    for m in messages:
        msg_id = m["id"]
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg_id, format="full")
            .execute()
        )
        payload = msg.get("payload", {})
        headers = {
            h["name"]: h["value"] for h in payload.get("headers", [])
        }
        subject = headers.get("Subject", "")
        sender = headers.get("From", "")
        body = get_message_body(payload)
        pdf_attachments: List[Dict] = []
        pdf_parts = collect_pdf_parts(payload)
        for part in pdf_parts:
            attach_id = part.get("body", {}).get("attachmentId")
            filename = part.get("filename") or f"{msg_id}.pdf"
            if not attach_id:
                continue
            attach = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=msg_id, id=attach_id)
                .execute()
            )
            data = attach.get("data")
            if not data:
                continue
            pdf_bytes = base64.urlsafe_b64decode(data + "===")
            pdf_attachments.append(
                {
                    "filename": filename,
                    "content": pdf_bytes,
                }
            )
        emails.append(
            {
                "id": msg_id,
                "from": sender,
                "subject": subject,
                "body": body,               # email text only
                "pdf_attachments": pdf_attachments,  # list of dicts
            }
        )
    return emails

if __name__ == "__main__":
    emails = fetch_order_emails(max_results=3)
    print("Fetched", len(emails), "emails\n")
    for e in emails:
        print("From:", e["from"])
        print("Subject:", e["subject"])
        print("Body preview:", e["body"][:300], "...\n")
        print("-" * 60)