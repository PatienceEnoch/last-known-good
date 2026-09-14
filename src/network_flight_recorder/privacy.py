"""Pseudonymize sensitive snapshot fields before storage or sharing."""

from __future__ import annotations

import copy
import hashlib
import hmac
from typing import Any


def _token(kind: str, value: Any, key: str) -> str:
    digest = hmac.new(key.encode(), str(value).encode(), hashlib.sha256).hexdigest()[:12]
    return f"{kind}-{digest}"


def redact_snapshot(snapshot: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a pseudonymized copy while preserving values needed for comparisons."""
    if not key:
        raise ValueError("A non-empty redaction key is required")
    result = copy.deepcopy(snapshot)
    host = result.get("host", {})
    if host.get("hostname"):
        host["hostname"] = _token("host", host["hostname"], key)

    network = result.get("network", {})
    network["dns_servers"] = [
        _token("ip", server, key) for server in network.get("dns_servers", [])
    ]
    for interface in network.get("interfaces", []):
        for address in interface.get("addresses", []):
            if address.get("local"):
                address["local"] = _token("ip", address["local"], key)
    for route in network.get("routes", []):
        for field in ("gateway", "prefsrc"):
            if route.get(field):
                route[field] = _token("ip", route[field], key)
    for probe in network.get("probes", []):
        if probe.get("host"):
            probe["host"] = _token("target", probe["host"], key)
    for probe in network.get("dns_probes", []):
        if probe.get("name"):
            probe["name"] = _token("name", probe["name"], key)
        probe["addresses"] = [
            _token("ip", address, key) for address in probe.get("addresses", [])
        ]
        if probe.get("error"):
            probe["error"] = "resolution failed (details redacted)"
    return result
