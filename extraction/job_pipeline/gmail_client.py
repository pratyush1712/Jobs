"""Gmail OAuth and message helpers."""

from __future__ import annotations

import os
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_GMAIL_CREDENTIALS_FILE,
    DEFAULT_GMAIL_TOKEN_FILE,
    EXTRACTION_DIR,
    GMAIL_SCOPES,
)
from .utils import build_gmail_link, decode_base64url


def _resolve_project_relative_path(path: str) -> str:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return str(candidate)
    return str(EXTRACTION_DIR / candidate)


def _google_imports() -> tuple[Any, Any, Any, Any]:
    """Import Google packages lazily so non-Gmail tests can run without them."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except Exception as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(
            "Google Gmail dependencies are missing. Install them with: "
            "pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2"
        ) from exc
    return Request, Credentials, InstalledAppFlow, build


def get_gmail_service(
    credentials_file: str | None = None, token_file: str = DEFAULT_GMAIL_TOKEN_FILE
) -> Any:
    Request, Credentials, InstalledAppFlow, build = _google_imports()
    credentials_file = _resolve_project_relative_path(
        credentials_file
        or os.getenv("GMAIL_CREDENTIALS_FILE", DEFAULT_GMAIL_CREDENTIALS_FILE)
    )
    token_file = _resolve_project_relative_path(token_file)
    creds = None
    Path(token_file).parent.mkdir(parents=True, exist_ok=True)
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(token_file, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def list_all_message_ids(
    service: Any, query: str, limit: int | None = None
) -> list[str]:
    ids: list[str] = []
    page_token = None
    while True:
        remaining = None if limit is None else max(limit - len(ids), 0)
        if remaining == 0:
            break
        max_results = min(500, remaining or 500)
        resp = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results, pageToken=page_token)
            .execute()
        )
        ids.extend([m["id"] for m in resp.get("messages", [])])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids[:limit] if limit else ids


def get_header(headers: list[dict[str, str]], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def extract_payload_bodies(payload: dict[str, Any]) -> dict[str, list[str]]:
    out = {"text/plain": [], "text/html": []}

    def walk(part: dict[str, Any]) -> None:
        mime = part.get("mimeType", "")
        body = part.get("body", {}) or {}
        data = body.get("data")
        if mime in out and data:
            out[mime].append(decode_base64url(data))
        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)
    return out


def read_message(service: Any, gmail_message_id: str) -> dict[str, Any]:
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=gmail_message_id, format="full")
        .execute()
    )
    payload = msg.get("payload", {}) or {}
    headers = payload.get("headers", []) or []
    date_header = get_header(headers, "Date")
    email_date = ""
    if date_header:
        try:
            email_date = parsedate_to_datetime(date_header).isoformat()
        except Exception:
            email_date = date_header

    message_id_header = get_header(headers, "Message-ID").strip().strip("<>")
    return {
        "gmail_internal_id": msg.get("id", ""),
        "thread_id": msg.get("threadId", ""),
        "sender": get_header(headers, "From"),
        "subject": get_header(headers, "Subject"),
        "date_header": date_header,
        "email_date": email_date,
        "message_id_header": message_id_header,
        "gmail_link": build_gmail_link(message_id_header),
        "snippet": msg.get("snippet", ""),
        "bodies": extract_payload_bodies(payload),
    }
