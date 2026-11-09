"""The live dashboard (rich) and the plain/JSON line output."""
import json
import time

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import __version__
from .model import country_name, mask_ip

# grimh3xx palette
ACCENT, ACCENT2 = "#3B82F6", "#22D3EE"
TITLE, TEXT, MUTED, DIM, BORDER = "#F1F5FB", "#C5CFDD", "#8B98AD", "#5B6678", "#1E2A3D"
OK, WARN, ERR = "#34D399", "#FBBF24", "#F87171"

BANNER = [
    "███╗   ██╗██╗   ██╗██╗  ██╗███╗   ██╗███████╗████████╗",
    "████╗  ██║╚██╗ ██╔╝╚██╗██╔╝████╗  ██║██╔════╝╚══██╔══╝",
    "██╔██╗ ██║ ╚████╔╝  ╚███╔╝ ██╔██╗ ██║█████╗     ██║   ",
    "██║╚██╗██║  ╚██╔╝   ██╔██╗ ██║╚██╗██║██╔══╝     ██║   ",
    "██║ ╚████║   ██║   ██╔╝ ██╗██║ ╚████║███████╗   ██║   ",
    "╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ",
]


def _mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def banner():
    out = Text()
    width = len(BANNER[0])
    for line in BANNER:
        for i, ch in enumerate(line):
            out.append(ch, style=_mix(ACCENT, ACCENT2, i / (width - 1)) if ch == "█" else DIM)
        out.append("\n")
    out.rstrip()
    return out


class State:
    def __init__(self, backend, history, real_ip, interval, count):
        self.backend, self.history, self.real_ip = backend, history, real_ip
        self.interval, self.count = interval, count
        self.status, self.status_color = "starting", WARN
        self.next_at = None
        self.paused = False

    def set_status(self, text, color=WARN):
        self.status, self.status_color = text, color

    @property
    def current(self):
        return self.history.items[-1] if self.history.items else None


def latency_color(ms):
    if ms is None:
        return DIM
    return OK if ms < 1500 else WARN if ms < 3500 else ERR


def _kv(rows):
    t = Table.grid(padding=(0, 2))
    t.add_column(style=MUTED, no_wrap=True)
    t.add_column(style=TEXT, no_wrap=True, overflow="ellipsis")
    for k, v in rows:
        t.add_row(k, v)
    return t


def _panel(body, title, subtitle=None):
    return Panel(body, title=Text(f" {title} ", style=f"bold {TITLE}"), title_align="left",
                 subtitle=subtitle, subtitle_align="right",
                 border_style=BORDER, box=box.ROUNDED, padding=(0, 1))


def stats(h):
    out = Text(" ")
    for label, val in (("rotations", len(h.items)), ("unique exits", h.unique_exits),
                       ("countries", h.countries), ("avg", f"{h.avg_latency} ms" if h.avg_latency else "—")):
        out += Text(f"{label} ", style=DIM) + Text(f"{val}  ", style=TEXT)
    return out


def header(st):
    b = st.backend
    mode = {"demo": ("demo · simulated network", WARN), "launched": ("private Tor instance", OK),
            "attached": ("attached to Tor Browser" if getattr(b, "control_port", 0) == 9151
                         else f"attached to ControlPort :{getattr(b, 'control_port', '')}", OK)}.get(b.mode, ("connecting", WARN))
    info = _kv([
        ("", Text("Tor identity rotator", style=f"bold {TITLE}")),
        ("", Text(f"v{__version__} · github.com/grimh3xx", style=DIM)),
        ("", ""),
        ("mode", Text("● ", style=mode[1]) + Text(mode[0])),
        ("socks5", Text(b.socks, style=ACCENT2)),
        ("status", Text("● ", style=st.status_color) + Text(st.status)),
    ])
    g = Table.grid(padding=(0, 4))
    g.add_row(banner(), info)
    return g


def identity_panel(st):
    cur = st.current
    if not cur:
        body = Text("waiting for the first circuit…", style=DIM)
    else:
        if cur.error:
            check = Text(f"✗ request failed ({cur.error})", style=ERR)
        elif cur.is_tor:
            check = Text("✓ ", style=OK) + Text("confirmed by check.torproject.org")
        else:
            check = Text("✗ traffic is NOT going through Tor", style=f"bold {ERR}")
        exit_ip = Text(cur.exit_ip or "—", style=f"bold {TITLE}")
        if cur.reused:
            exit_ip += Text("  ↺ seen before", style=WARN)
        body = _kv([
            ("exit ip", exit_ip),
            ("location", Text(f"{cur.country} · {country_name(cur.country)}")),
            ("tor check", check),
            ("latency", Text(f"{cur.latency_ms} ms" if cur.latency_ms is not None else "—")),
            ("real ip", Text(mask_ip(st.real_ip) if st.real_ip else "hidden", style=DIM)),
        ])
    return _panel(body, "Identity")


def circuit_panel(st):
    cur = st.current
    if not cur or not cur.path:
        return _panel(Text("circuit details unavailable" if cur else "building circuit…", style=DIM), "Circuit")
    t = Table.grid(padding=(0, 1))
    t.add_column(width=2)
    t.add_column(style=MUTED, width=7)
    t.add_column(style=TEXT, no_wrap=True, overflow="ellipsis", max_width=18)
    t.add_column(style=ACCENT2, width=3)
    t.add_column(style=DIM, no_wrap=True)
    t.add_row(Text("◉", style=ACCENT), "you", Text(mask_ip(st.real_ip) if st.real_ip else "this machine", style=DIM), "", "")
    for hop in cur.path:
        t.add_row(Text("│", style=DIM), "", "", "", "")
        color = ACCENT2 if hop.role == "exit" else ACCENT
        t.add_row(Text("●", style=color), hop.role, hop.nickname, hop.country, hop.address)
    return _panel(t, "Circuit")


def rotations(st, rows):
    t = Table(box=box.SIMPLE_HEAD, border_style=BORDER, header_style=f"bold {MUTED}", expand=True, padding=(0, 1))
    t.add_column("#", style=DIM, justify="right", width=3)
    t.add_column("time", style=MUTED, width=8)
    t.add_column("exit ip", style=TITLE, no_wrap=True, min_width=15)
    t.add_column("cc", style=ACCENT2, width=3)
    t.add_column("circuit", style=TEXT, no_wrap=True, overflow="ellipsis", ratio=1)
    t.add_column("latency", justify="right", width=8)
    t.add_column("", width=8)
    for i in st.history.items[-rows:][::-1]:
        if i.error or not i.exit_ip:
            flag = Text("✗ failed", style=ERR)
        elif not i.is_tor:
            flag = Text("✗ no tor", style=ERR)
        elif i.reused:
            flag = Text("↺ reused", style=WARN)
        else:
            flag = Text("✓ new", style=OK)
        lat = i.latency_ms
        lat_t = Text(f"{lat} ms" if lat is not None else "—", style=latency_color(lat))
        t.add_row(str(i.n), f"{i.at:%H:%M:%S}", i.exit_ip or "—", i.country,
                  " → ".join(h.nickname for h in i.path) or "—", lat_t, flag)
    return _panel(t, "Rotations", stats(st.history))


def footer(st, width):
    if st.paused:
        line = Text("⏸ paused", style=WARN)
    elif st.next_at is None:
        line = Text("● rotating…", style=ACCENT2)
    else:
        left = max(0.0, st.next_at - time.monotonic())
        frac = 1 - left / st.interval if st.interval else 1
        n = 28
        filled = round(n * frac)
        line = Text("next identity in ", style=MUTED) + Text(f"{left:4.1f}s ", style=TITLE)
        line += Text("━" * filled, style=ACCENT2) + Text("━" * (n - filled), style=BORDER)
    keys = Text()
    for k, label in (("n", "new identity"), ("p", "pause"), ("q", "quit")):
        keys += Text(f" {k} ", style=f"bold {ACCENT2}") + Text(f"{label}  ", style=DIM)
    g = Table.grid(expand=True)
    g.add_column(no_wrap=True)
    g.add_column(justify="right", no_wrap=True)
    g.add_row(line, keys)
    return g


def render(st, size):
    w, h = size
    top = Table.grid(expand=True, padding=(0, 1))
    top.add_column(ratio=5)
    top.add_column(ratio=6)
    top.add_row(identity_panel(st), circuit_panel(st))
    rows = max(2, h - 26)
    return Group(Text(""), header(st), Text(""), top, rotations(st, rows), footer(st, w))


# ------------------------------------------------------------- line output
def plain_line(i):
    if i.error or not i.exit_ip:
        return f"[{i.at:%H:%M:%S}] #{i.n:<3} failed ({i.error or 'no exit IP'})"
    path = " → ".join(h.nickname for h in i.path) or "?"
    verdict = "tor ✓" if i.is_tor else "NOT TOR ✗"
    reused = "  (reused)" if i.reused else ""
    return (f"[{i.at:%H:%M:%S}] #{i.n:<3} {i.exit_ip:<15} {i.country:<2}  {i.latency_ms:>4} ms  "
            f"{verdict}  via {path}{reused}")


def json_line(i):
    return json.dumps(i.to_json())
