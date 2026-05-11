"""IMAP-based approval checker."""

from __future__ import annotations

import email
import imaplib
import logging
import re
from dataclasses import dataclass
from email.header import decode_header
from typing import Literal


Decision = Literal["APPROVE", "DENY"]


@dataclass(slots=True)
class ApprovalResult:
    """Represents an approval decision found in mailbox."""

    decision: Decision
    message_id: str


class ApprovalChecker:
    """Checks unread mailbox messages for approval decisions."""

    def __init__(
        self,
        imap_host: str,
        imap_port: int,
        username: str,
        password: str,
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.username = username
        self.password = password

    def check(self, approval_id: str) -> ApprovalResult | None:
        """Return latest decision for an approval ID, if any."""
        with imaplib.IMAP4_SSL(self.imap_host, self.imap_port, timeout=30) as mail:
            self.logger.info("Checking mailbox for approval ID=%s", approval_id)
            mail.login(self.username, self.password)
            mail.select("INBOX")
            status, data = mail.search(None, "TEXT", f'"{approval_id}"')
            if status != "OK":
                self.logger.error("Failed to search emails for approval ID=%s.", approval_id)
                return None

            message_nums = data[0].split()
            self.logger.info(
                "Mailbox search returned %d candidate message(s) for approval ID=%s",
                len(message_nums),
                approval_id,
            )
            # Iterate newest first so we react to the latest reviewer action.
            for msg_num in reversed(message_nums):
                status, msg_data = mail.fetch(msg_num, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw_email = msg_data[0][1]
                if not isinstance(raw_email, bytes):
                    continue

                parsed = email.message_from_bytes(raw_email)
                subject = self._decode_header(parsed.get("Subject", ""))
                body = self._extract_body(parsed)
                content = f"{subject}\n{body}".upper()

                # Ignore unrelated messages; decision must carry current approval token.
                if f"ID:{approval_id}".upper() not in content and approval_id.upper() not in content:
                    continue

                decision = self._parse_decision(content)
                if decision:
                    # Mark handled so we do not process the same decision again next run.
                    mail.store(msg_num, "+FLAGS", "\\Seen")
                    message_id = parsed.get("Message-ID", f"msg-{msg_num.decode(errors='ignore')}")
                    self.logger.info("Found decision=%s for approval ID=%s", decision, approval_id)
                    return ApprovalResult(decision=decision, message_id=message_id)

            return None

    @staticmethod
    def _parse_decision(content: str) -> Decision | None:
        # Keep YES/NO compatibility for older approval templates.
        if re.search(r"\bAPPROVE\b", content) or re.search(r"\bYES\b", content):
            return "APPROVE"
        if re.search(r"\bDENY\b", content) or re.search(r"\bNO\b", content):
            return "DENY"
        return None

    @staticmethod
    def _decode_header(value: str) -> str:
        parts = decode_header(value)
        decoded = []
        for part, encoding in parts:
            if isinstance(part, bytes):
                decoded.append(ApprovalChecker._decode_bytes(part, encoding))
            else:
                decoded.append(part)
        return "".join(decoded)

    @staticmethod
    def _extract_body(message: email.message.Message) -> str:
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        return ApprovalChecker._decode_bytes(payload, part.get_content_charset())
        else:
            payload = message.get_payload(decode=True)
            if isinstance(payload, bytes):
                return ApprovalChecker._decode_bytes(payload, message.get_content_charset())
            if isinstance(payload, str):
                return payload
        return ""

    @staticmethod
    def _decode_bytes(raw: bytes, encoding: str | None) -> str:
        """Decode bytes with defensive fallback for invalid mail encodings."""
        normalized = (encoding or "utf-8").strip().lower()
        if normalized in {"unknown-8bit", "x-unknown", "unknown"}:
            normalized = "utf-8"

        try:
            return raw.decode(normalized, errors="ignore")
        except LookupError:
            return raw.decode("utf-8", errors="ignore")
