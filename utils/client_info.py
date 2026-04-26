from __future__ import annotations

import ipaddress

import streamlit as st


def _safe_headers() -> dict:
    # Streamlit >= 1.30 exposes request headers in st.context.headers
    try:
        ctx = getattr(st, "context", None)
        headers = getattr(ctx, "headers", None) if ctx else None
        return dict(headers) if headers else {}
    except Exception:
        return {}


def get_header_value(name: str) -> str:
    if not name:
        return ""
    h = _safe_headers()
    # headers may come in various casings
    for k, v in h.items():
        if str(k).lower() == str(name).lower():
            return str(v).strip()
    return ""


def get_client_ip() -> str:
    h = _safe_headers()
    # Common proxy/CDN headers (order matters: prefer "direct client" headers).
    direct = (
        h.get("cf-connecting-ip")
        or h.get("CF-Connecting-IP")
        or h.get("true-client-ip")
        or h.get("True-Client-Ip")
        or h.get("x-client-ip")
        or h.get("X-Client-Ip")
        or h.get("x-real-ip")
        or h.get("X-Real-IP")
    )
    if direct:
        return str(direct).strip()

    xff = (h.get("x-forwarded-for") or h.get("X-Forwarded-For") or "").strip()
    if xff:
        # First IP is the original client; proxies append afterwards.
        return xff.split(",")[0].strip()

    fwd = (h.get("forwarded") or h.get("Forwarded") or "").strip()
    # Forwarded: for=1.2.3.4;proto=https;by=...
    if "for=" in fwd.lower():
        try:
            parts = fwd.split("for=", 1)[1]
            token = parts.split(";", 1)[0].strip().strip('"').strip()
            # token may include IPv6 in brackets: for="[2001:db8::1]"
            token = token.strip("[]")
            return token
        except Exception:
            return ""

    return ""


def is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return not (addr.is_private or addr.is_loopback or addr.is_multicast or addr.is_reserved or addr.is_link_local)
    except Exception:
        return False


def get_client_location(ip: str) -> str:
    """
    Best-effort lookup. Returns "" if unavailable.
    Uses ipapi.co without an API key (suitable for light usage).
    """
    ip = (ip or "").strip()
    if not ip:
        return ""
    if not is_public_ip(ip):
        return "Private network"
    try:
        import requests

        resp = requests.get(f"https://ipapi.co/{ip}/json/", timeout=2)
        if resp.status_code != 200:
            return ""
        data = resp.json() if isinstance(resp.json(), dict) else {}
        city = (data.get("city") or "").strip()
        region = (data.get("region") or "").strip()
        country = (data.get("country_name") or "").strip()
        parts = [p for p in [city, region, country] if p]
        return ", ".join(parts)[:120]
    except Exception:
        return ""


def get_client_ip_and_location() -> tuple[str, str]:
    ip = get_client_ip()
    loc = get_client_location(ip) if ip else ""
    return ip, loc

