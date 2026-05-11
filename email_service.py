"""SMTP email delivery service for approval workflows."""

from __future__ import annotations

import logging
import smtplib
from html import escape
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote


class EmailService:
    """Sends approval requests to a human reviewer via SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        email_from: str,
        email_to: str,
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.email_from = email_from
        self.email_to = email_to

    def send_approval_request(
        self,
        approval_id: str,
        topic_title: str,
        post_text: str,
        attempt: int,
    ) -> None:
        """Send approval request email with generated post content."""
        # These links create prefilled emails so reviewer can click instead of typing commands.
        approve_mailto = self._build_mailto_link(approval_id=approval_id, decision="APPROVE")
        deny_mailto = self._build_mailto_link(approval_id=approval_id, decision="DENY")

        msg = MIMEMultipart()
        msg["From"] = self.email_from
        msg["To"] = self.email_to
        msg["Subject"] = f"Approve LinkedIn Post? (Use Buttons) [ID:{approval_id}]"

        body = (
            "LinkedIn Content Approval Request\n\n"
            f"Approval ID: {approval_id}\n"
            f"Regeneration Attempt: {attempt}\n\n"
            f"Selected Topic:\n{topic_title}\n\n"
            "Generated LinkedIn Post:\n"
            f"{post_text}\n\n"
            "Instructions:\n"
            "Click APPROVE or DENY button below.\n"
            "This opens your mail client with a prefilled decision.\n"
            "Do not edit the approval token.\n\n"
            f"APPROVE: {approve_mailto}\n"
            f"DENY: {deny_mailto}"
        )
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #1f2937;">
            <h3>LinkedIn Content Approval Request</h3>
            <p><strong>Approval ID:</strong> {approval_id}</p>
            <p><strong>Regeneration Attempt:</strong> {attempt}</p>
            <p><strong>Selected Topic:</strong><br>{escape(topic_title)}</p>
            <p><strong>Generated LinkedIn Post:</strong></p>
            <pre style="white-space: pre-wrap; background: #f9fafb; padding: 12px; border: 1px solid #e5e7eb;">{escape(post_text)}</pre>
            <p>Review and choose one action:</p>
            <p>
              <a href="{approve_mailto}" style="display: inline-block; padding: 10px 16px; margin-right: 10px; background: #059669; color: #ffffff; text-decoration: none; border-radius: 4px;">Approve</a>
              <a href="{deny_mailto}" style="display: inline-block; padding: 10px 16px; background: #dc2626; color: #ffffff; text-decoration: none; border-radius: 4px;">Deny</a>
            </p>
            <p>If buttons are blocked by your client, use the plain links in the text version.</p>
          </body>
        </html>
        """
        # Send both plain and HTML for better client compatibility.
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.email_from, self.email_to, msg.as_string())

        self.logger.info("Sent approval request for ID=%s attempt=%d", approval_id, attempt)

    def _build_mailto_link(self, approval_id: str, decision: str) -> str:
        subject = quote(f"{decision} [ID:{approval_id}]")
        body = quote(f"Decision={decision}\nApproval ID={approval_id}")
        return f"mailto:{self.email_from}?subject={subject}&body={body}"
