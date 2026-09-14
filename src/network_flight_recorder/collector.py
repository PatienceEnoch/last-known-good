"""Collect a defensive snapshot of local Linux network state."""

from __future__ import annotations

import json
import platform
import re
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _run(command: list[str], timeout: int = 5) -> dict[str, Any]:
    """Run a read-only diagnostic command without failing the entire snapshot."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
        return {
            "available": True,
            "return_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except FileNotFoundError:
        return {"available": False, "return_code": None, "stdout": "", "stderr": "not found"}
    except subprocess.TimeoutExpired:
        return {"available": True, "return_code": None, "stdout": "", "stderr": "timed out"}


def _json_command(command: list[str]) -> list[dict[str, Any]]:
    result = _run(command)
    if result["return_code"] != 0 or not result["stdout"]:
        return []
    try:
        value = json.loads(result["stdout"])
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def _dns_servers(path: Path = Path("/etc/resolv.conf")) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    return re.findall(r"^nameserver\s+(\S+)", text, flags=re.MULTILINE)


def _interfaces() -> list[dict[str, Any]]:
    interfaces = []
    for item in _json_command(["ip", "-json", "address", "show"]):
        addresses = []
        for address in item.get("addr_info", []):
            if address.get("family") in {"inet", "inet6"}:
                addresses.append(
                    {
                        "family": address.get("family"),
                        "local": address.get("local"),
                        "prefixlen": address.get("prefixlen"),
                    }
                )
        interfaces.append(
            {
                "name": item.get("ifname"),
                "state": item.get("operstate", "UNKNOWN"),
                "mtu": item.get("mtu"),
                "addresses": addresses,
            }
        )
    return interfaces


def _routes() -> list[dict[str, Any]]:
    keep = {"dst", "gateway", "dev", "protocol", "metric", "prefsrc"}
    return [
        {key: value for key, value in route.items() if key in keep}
        for route in _json_command(["ip", "-json", "route", "show"])
    ]


def _failed_services() -> list[str]:
    result = _run(["systemctl", "--failed", "--no-legend", "--plain"])
    if result["return_code"] != 0:
        return []
    services = []
    for line in result["stdout"].splitlines():
        parts = line.split()
        if parts:
            services.append(parts[0])
    return services


def _probe(host: str) -> dict[str, Any]:
    result = _run(["ping", "-c", "3", "-W", "2", host], timeout=8)
    latency = None
    packet_loss_percent = None
    match = re.search(r"= [\d.]+/([\d.]+)/", result["stdout"])
    if match:
        latency = float(match.group(1))
    loss_match = re.search(r"([\d.]+)% packet loss", result["stdout"])
    if loss_match:
        packet_loss_percent = float(loss_match.group(1))
    return {
        "host": host,
        "reachable": result["return_code"] == 0,
        "average_latency_ms": latency,
        "packet_loss_percent": packet_loss_percent,
    }


def _dns_probe(name: str) -> dict[str, Any]:
    """Resolve a name through the host's configured resolver and record timing."""
    started = time.monotonic()
    try:
        results = socket.getaddrinfo(name, None, type=socket.SOCK_STREAM)
        addresses = sorted({item[4][0] for item in results})
        error = None
    except socket.gaierror as exc:
        addresses = []
        error = str(exc)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    return {
        "name": name,
        "resolved": bool(addresses),
        "response_time_ms": elapsed_ms,
        "addresses": addresses,
        "error": error,
    }


def collect_snapshot(
    probe_hosts: list[str] | None = None, dns_names: list[str] | None = None
) -> dict[str, Any]:
    """Return a JSON-serializable snapshot. Collection is local and read-only."""
    probe_hosts = probe_hosts or []
    dns_names = dns_names or []
    return {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "host": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
        },
        "network": {
            "dns_servers": _dns_servers(),
            "interfaces": _interfaces(),
            "routes": _routes(),
            "probes": [_probe(host) for host in probe_hosts],
            "dns_probes": [_dns_probe(name) for name in dns_names],
        },
        "system": {"failed_services": _failed_services()},
    }
