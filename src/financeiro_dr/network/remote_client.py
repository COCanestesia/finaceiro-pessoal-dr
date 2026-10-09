from __future__ import annotations

import json
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class RemoteReadClient:
    """Read-only API client. Remote transport must use HTTPS through private VPN."""

    def __init__(self, base_url: str):
        parsed = urlsplit(base_url)
        local = parsed.hostname in ("127.0.0.1", "localhost")
        if (parsed.scheme != "https" and not (local and parsed.scheme == "http")) or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Use HTTPS para acesso remoto ou HTTP somente no computador local.")
        self.base_url = base_url.rstrip("/")
        self.token = None

    def _request(self, path: str, payload: dict | None = None):
        headers = {"Accept": "application/json"}
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = Request(self.base_url + path, data=body, headers=headers)
        with urlopen(request, timeout=8) as response:
            return json.load(response)

    def login(self, username: str, password: str) -> dict:
        response = self._request("/v1/session", {"username": username, "password": password})
        self.token = response["token"]
        return response["user"]

    def create_entry(self, competence_date: str, description: str, amount_cents: int,
                     entry_type: str, status: str) -> int:
        if not self.token:
            raise PermissionError("Faça login antes de registrar.")
        response = self._request("/v1/entries", {
            "competence_date": competence_date, "description": description,
            "amount_cents": amount_cents, "entry_type": entry_type, "status": status,
        })
        return int(response["id"])

    def entries(self) -> list[dict]:
        if not self.token:
            raise PermissionError("Faça login antes de consultar.")
        return self._request("/v1/entries")["entries"]
