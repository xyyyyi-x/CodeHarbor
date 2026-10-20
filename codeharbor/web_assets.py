# 来源：公众号@小林coding
# 后端八股网站：xiaolincoding.com
# Agent网站：xiaolinnote.com
# 简历模版：jianli.xiaolinnote.com

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True, slots=True)
class WebAsset:
    body: bytes
    content_type: str
    cache_control: str


_ROOT_ASSETS = {"index.html", "styles.css", "app.js"}
_ALLOWED_DIRECTORIES = {"assets", "vendor"}
_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
}


def load_web_asset(request_path: str) -> WebAsset | None:
    """Load an explicitly allowed package resource for an HTTP request path."""
    decoded = unquote(urlsplit(request_path).path)
    if "\\" in decoded or "\x00" in decoded:
        return None

    relative = decoded.lstrip("/") or "index.html"
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    if len(parts) == 1:
        if parts[0] not in _ROOT_ASSETS:
            return None
    elif parts[0] not in _ALLOWED_DIRECTORIES:
        return None

    suffix = "." + parts[-1].rsplit(".", 1)[-1].lower() if "." in parts[-1] else ""
    content_type = _CONTENT_TYPES.get(suffix)
    if content_type is None:
        return None

    resource = files("codeharbor.web").joinpath(*parts)
    if not resource.is_file():
        return None
    cache_control = "no-cache" if parts[-1] == "index.html" else "public, max-age=3600"
    return WebAsset(resource.read_bytes(), content_type, cache_control)
