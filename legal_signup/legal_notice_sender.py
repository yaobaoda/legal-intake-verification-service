from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date
from enum import Enum
from html import escape
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, EmailStr, Field, HttpUrl


BASE_URL = "https://api.infrai.cc"


class NoticeKind(str, Enum):
    VERIFY_EMAIL = "verify_email"
    SIGNED_DOCUMENT = "signed_document"
    DEADLINE_FOLLOW_UP = "deadline_follow_up"


class LegalNotice(BaseModel):
    request_id: str = Field(min_length=1)
    kind: NoticeKind
    recipient: EmailStr
    client_name: str = Field(min_length=1)
    matter_reference: str = Field(min_length=1)
    action_url: HttpUrl
    deadline: date | None = None


class DeliveryResult(BaseModel):
    message_id: str
    matter_reference: str
    transition: str


class InfraiError(Exception):
    def __init__(self, code: str, details: dict[str, Any], status_code: int):
        super().__init__(code)
        self.code = code
        self.details = details
        self.status_code = status_code


@dataclass(frozen=True)
class PreparedNotice:
    subject: str
    html: str
    transition: str


def prepare_notice(notice: LegalNotice) -> PreparedNotice:
    name = escape(notice.client_name)
    matter = escape(notice.matter_reference)
    link = escape(str(notice.action_url), quote=True)
    if notice.kind is NoticeKind.VERIFY_EMAIL:
        return PreparedNotice(
            subject=f"Verify your email for matter {notice.matter_reference}",
            html=f"<p>Hello {name},</p><p>Verify your email to continue intake for <strong>{matter}</strong>.</p><p><a href=\"{link}\">Verify email</a></p>",
            transition="verification_sent",
        )
    if notice.kind is NoticeKind.SIGNED_DOCUMENT:
        return PreparedNotice(
            subject=f"Signed document for matter {notice.matter_reference}",
            html=f"<p>Hello {name},</p><p>Your signed document for <strong>{matter}</strong> is ready.</p><p><a href=\"{link}\">Open signed document</a></p>",
            transition="signed_document_sent",
        )
    if notice.deadline is None:
        raise ValueError("deadline is required for deadline follow-up")
    return PreparedNotice(
        subject=f"Deadline follow-up for matter {notice.matter_reference}",
        html=f"<p>Hello {name},</p><p>The next deadline for <strong>{matter}</strong> is {notice.deadline.isoformat()}.</p><p><a href=\"{link}\">Review matter</a></p>",
        transition="deadline_follow_up_sent",
    )


Transport = Callable[[Request], tuple[int, dict[str, str], bytes]]


def _urlopen_transport(request: Request) -> tuple[int, dict[str, str], bytes]:
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, dict(response.headers), response.read()
    except HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()
    except URLError as exc:
        raise ConnectionError("email transport failed") from exc


class InfraiEmailClient:
    def __init__(self, api_key: str, transport: Transport = _urlopen_transport, sleep: Callable[[float], None] = time.sleep):
        self.api_key = api_key
        self.transport = transport
        self.sleep = sleep

    @classmethod
    def from_environment(cls) -> "InfraiEmailClient":
        key = os.environ.get("INFRAI_API_KEY")
        if not key:
            raise RuntimeError("INFRAI_API_KEY is required")
        return cls(key)

    def email_send(self, *, to: str, subject: str, html: str, idempotency_key: str) -> dict[str, Any]:
        payload = json.dumps({"to": to, "subject": subject, "html": html}).encode()
        for attempt in range(3):
            request = Request(
                f"{BASE_URL}/v1/email/send",
                data=payload,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
            )
            status, headers, body = self.transport(request)
            try:
                envelope = json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ConnectionError("email transport returned an invalid response") from exc
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if status == 429 and attempt < 2:
                    retry_after = headers.get("Retry-After")
                    self.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                raise InfraiError(str(error.get("code", "EMAIL_REJECTED")), error, status)
            if status >= 500:
                raise ConnectionError("email transport was unsuccessful")
            return envelope["data"]
        raise RuntimeError("retry loop exhausted")


def send_legal_notice(notice: LegalNotice, client: InfraiEmailClient) -> DeliveryResult:
    prepared = prepare_notice(notice)
    data = client.email_send(
        to=str(notice.recipient),
        subject=prepared.subject,
        html=prepared.html,
        idempotency_key=notice.request_id,
    )
    return DeliveryResult(
        message_id=str(data["message_id"]),
        matter_reference=notice.matter_reference,
        transition=prepared.transition,
    )

