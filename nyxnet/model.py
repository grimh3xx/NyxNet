"""Data shared by the backends, the dashboard and the history log."""
import ipaddress
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

COUNTRIES = {
    "AT": "Austria", "AU": "Australia", "BE": "Belgium", "BG": "Bulgaria", "BR": "Brazil", "CA": "Canada",
    "CH": "Switzerland", "CZ": "Czechia", "DE": "Germany", "DK": "Denmark", "EE": "Estonia", "ES": "Spain",
    "FI": "Finland", "FR": "France", "GB": "United Kingdom", "HK": "Hong Kong", "HU": "Hungary",
    "IE": "Ireland", "IS": "Iceland", "IT": "Italy", "JP": "Japan", "LT": "Lithuania", "LU": "Luxembourg",
    "LV": "Latvia", "MD": "Moldova", "NL": "Netherlands", "NO": "Norway", "NZ": "New Zealand",
    "PL": "Poland", "PT": "Portugal", "RO": "Romania", "RS": "Serbia", "SE": "Sweden", "SG": "Singapore",
    "SK": "Slovakia", "UA": "Ukraine", "US": "United States",
}


class TorError(Exception):
    """Tor is missing, unreachable or refused us: reported as one line, not a traceback."""


def country_name(code):
    if not code or code in ("??", "--"):
        return "unknown"
    return COUNTRIES.get(code.upper(), code.upper())


def mask_ip(ip):
    """Hide the middle of an address so it can be shown on screen or in a recording."""
    if not ip:
        return "—"
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return "•••"
    if addr.version == 4:
        a, _, _, d = ip.split(".")
        return f"{a}.•••.•••.{d}"
    return ip.split(":")[0] + ":•••:•••"


@dataclass
class Hop:
    role: str          # guard, middle, exit
    nickname: str
    fingerprint: str
    address: str = ""
    country: str = "??"


@dataclass
class Identity:
    n: int
    at: datetime
    exit_ip: str = None
    country: str = "??"
    is_tor: bool = None     # verdict from check.torproject.org
    latency_ms: int = None
    path: list = field(default_factory=list)
    reused: bool = False    # exit IP already seen earlier in this session
    error: str = None

    def to_json(self):
        d = asdict(self)
        d["at"] = self.at.isoformat(timespec="seconds")
        return d


class History:
    def __init__(self, log_path=None):
        self.items = []
        self.log_path = log_path

    def add(self, ident):
        ident.reused = bool(ident.exit_ip) and any(i.exit_ip == ident.exit_ip for i in self.items)
        self.items.append(ident)
        if self.log_path:
            try:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(ident.to_json()) + "\n")
            except OSError:
                self.log_path = None  # unwritable: keep running without the log

    @property
    def ok(self):
        return [i for i in self.items if i.exit_ip]

    @property
    def unique_exits(self):
        return len({i.exit_ip for i in self.ok})

    @property
    def countries(self):
        return len({i.country for i in self.ok if i.country not in ("??", None)})

    @property
    def avg_latency(self):
        lat = [i.latency_ms for i in self.ok if i.latency_ms is not None]
        return round(sum(lat) / len(lat)) if lat else None


def default_log_path():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or "~"
    else:
        base = os.environ.get("XDG_STATE_HOME") or "~/.local/state"
    return Path(base).expanduser() / "nyxnet" / "history.jsonl"
