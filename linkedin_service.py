"""LinkedIn Posts API publishing service."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(slots=True)
class LinkedInPostResult:
    """Result returned after LinkedIn accepts a post."""

    post_id: str


class LinkedInService:
    """Publishes approved text posts through LinkedIn's Posts API."""

    api_url = "https://api.linkedin.com/rest/posts"
    ugc_api_url = "https://api.linkedin.com/v2/ugcPosts"

    def __init__(
        self,
        access_token: str,
        author_urn: str,
        api_version: str,
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.access_token = access_token
        self.author_urn = author_urn
        self.api_version = api_version

    def publish_text_post(self, post_text: str) -> LinkedInPostResult:
        """Publish a public text-only post and return LinkedIn's post URN."""
        if self.author_urn.startswith(("urn:li:member:", "urn:li:company:")):
            return self._publish_via_ugc_api(post_text)

        try:
            return self._publish_via_posts_api(post_text)
        except RuntimeError as exc:
            if "status 403" not in str(exc):
                raise

            self.logger.warning(
                "LinkedIn Posts API returned 403. Retrying with UGC API for Share on LinkedIn."
            )
            return self._publish_via_ugc_api(post_text)

    def _publish_via_posts_api(self, post_text: str) -> LinkedInPostResult:
        payload = {
            "author": self.author_urn,
            "commentary": post_text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            self.api_url,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Linkedin-Version": self.api_version,
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )
        return self._send_publish_request(request)

    def _publish_via_ugc_api(self, post_text: str) -> LinkedInPostResult:
        payload = {
            "author": self.author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            self.ugc_api_url,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )

        return self._send_publish_request(request)

    def _send_publish_request(self, request: Request) -> LinkedInPostResult:
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed trusted API URL
                post_id = response.headers.get("x-restli-id", "").strip()
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            self.logger.error("LinkedIn publish failed: status=%s body=%s", exc.code, body)
            hint = self._failure_hint(exc.code)
            raise RuntimeError(
                f"LinkedIn publish failed with status {exc.code}: {body}{hint}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"LinkedIn publish failed: {exc.reason}") from exc

        if not post_id:
            raise RuntimeError("LinkedIn publish succeeded but response did not include x-restli-id.")

        self.logger.info("LinkedIn post published: %s", post_id)
        return LinkedInPostResult(post_id=post_id)

    def _failure_hint(self, status_code: int) -> str:
        if status_code != 403:
            return ""

        return (
            " Hint: LinkedIn returned Forbidden. Check that the access token was created "
            "with the w_member_social scope and that LINKEDIN_AUTHOR_URN matches the "
            "authenticated author. For UGC publishing use urn:li:member:<numeric_id> "
            "or urn:li:company:<numeric_id>."
        )
