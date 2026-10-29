"""Optional browser Basic login and Bearer API authentication."""

import base64
import binascii
from hmac import compare_digest
from urllib.parse import urlparse


class DashboardAuth:
    def __init__(self, password: str = "", token: str = "", username: str = "owner") -> None:
        self.password = password
        self.token = token
        self.username = username

    @property
    def enabled(self) -> bool:
        return bool(self.password or self.token)

    def authorized(self, header: str) -> bool:
        scheme, _, value = header.partition(" ")
        if scheme.lower() == "bearer" and self.token:
            return compare_digest(value.encode(), self.token.encode())
        if scheme.lower() == "basic" and self.password:
            try:
                credentials = base64.b64decode(value, validate=True).decode("utf-8")
            except (ValueError, binascii.Error, UnicodeDecodeError):
                return False
            return compare_digest(credentials.encode(), f"{self.username}:{self.password}".encode())
        return False

    def origin_allowed(self, origin: str | None, host: str) -> bool:
        if origin is None:
            return True
        parsed = urlparse(origin)
        return parsed.scheme in {"http", "https"} and parsed.netloc == host
