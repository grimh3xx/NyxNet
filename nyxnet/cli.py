"""Command line entry point: argument parsing and the rotation loop."""
import argparse
import os
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.live import Live

from . import __version__, ui
from .demo import DemoBackend, demo_real_ip
from .keys import KeyReader
from .model import History, TorError, default_log_path

NEWNYM_MIN = 10  # Tor rate-limits NEWNYM; shorter intervals would just queue up


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="nyxnet", description="Rotate your Tor identity on a timer and watch every circuit live.",
        epilog="Without a running Tor ControlPort, NyxNet launches a private Tor instance (no root, no torrc edits).")
    p.add_argument("-i", "--interval", type=float, default=15, metavar="SEC", help="seconds between new identities (default 15, min 10)")
    p.add_argument("-n", "--count", type=int, default=0, metavar="N", help="stop after N identities (default: run until q / Ctrl-C)")
    p.add_argument("--once", action="store_true", help="print the current Tor exit and quit")
    out = p.add_mutually_exclusive_group()
    out.add_argument("--plain", action="store_true", help="one line per identity instead of the dashboard")
    out.add_argument("--json", action="store_true", help="one JSON object per identity (for scripts)")

    tor = p.add_argument_group("tor")
    tor.add_argument("--socks-port", type=int, default=9050, metavar="PORT", help="SocksPort of an existing Tor (default 9050)")
    tor.add_argument("--control-port", type=int, default=9051, metavar="PORT", help="ControlPort of an existing Tor (default 9051)")
    tor.add_argument("--password", default=os.environ.get("NYXNET_TOR_PASSWORD"), help="ControlPort password (or NYXNET_TOR_PASSWORD); cookie auth is tried by default")
    tor.add_argument("--launch", choices=("auto", "always", "never"), default="auto", help="start a private Tor: auto = only if none is running (default)")
    tor.add_argument("--tor-cmd", default="tor", metavar="PATH", help="tor binary used with --launch")
    tor.add_argument("--timeout", type=float, default=20, metavar="SEC", help="timeout for each check through Tor (default 20)")

    misc = p.add_argument_group("other")
    misc.add_argument("--no-real-ip", action="store_true", help="never look up your real IP (it is only ever shown masked)")
    misc.add_argument("--log", type=Path, metavar="FILE", help=f"history file (default {default_log_path()})")
    misc.add_argument("--no-log", action="store_true", help="don't write a history file")
    misc.add_argument("--demo", action="store_true", help="simulated network: try the dashboard without Tor")
    misc.add_argument("--demo-speed", type=float, default=1.0, help=argparse.SUPPRESS)
    misc.add_argument("-V", "--version", action="version", version=f"nyxnet {__version__}")
    args = p.parse_args(argv)
    if args.once:
        args.count, args.plain = 1, not args.json
    return args


def make_backend(args, on_status):
    if args.demo:
        return DemoBackend(speed=args.demo_speed, on_status=on_status)
    from .tor import TorBackend  # stem/requests are only needed for the real thing
    return TorBackend(socks_port=args.socks_port, control_port=args.control_port, password=args.password,
                      launch=args.launch, tor_cmd=args.tor_cmd, timeout=args.timeout, on_status=on_status)


def lookup_real_ip(args):
    if args.no_real_ip:
        return None
    if args.demo:
        return demo_real_ip()
    from .tor import real_ip
    return real_ip()


def rotate(backend, on_status):
    wait = backend.newnym_wait()
    if wait > 0:
        on_status(f"Tor rate limit · new identity in {wait:.0f}s")
    backend.newnym()


def run_dashboard(args, backend, history, st, console):
    with Live(console=console, screen=True, auto_refresh=False, get_renderable=lambda: ui.render(st, console.size)) as live, \
            KeyReader() as keys:
        def status(text, color=ui.WARN):
            st.set_status(text, color)
            live.refresh()

        backend.on_status = status
        backend.start()
        st.real_ip = lookup_real_ip(args)
        n = 0
        while True:
            n += 1
            st.next_at = None
            status("checking exit through Tor…", ui.ACCENT2)
            ident = backend.identity(n)
            history.add(ident)
            status("circuit ready" if ident.is_tor else "check failed", ui.OK if ident.is_tor else ui.ERR)
            if args.count and n >= args.count:
                time.sleep(2 / args.demo_speed if args.demo else 0)
                return
            st.next_at = time.monotonic() + args.interval
            while True:
                key = keys.get(0.1)
                if key == "q":
                    return
                if key == "n":
                    break
                if key == "p":
                    st.paused = not st.paused
                    if st.paused:
                        remaining = st.next_at - time.monotonic()
                    else:
                        st.next_at = time.monotonic() + remaining
                if not st.paused and time.monotonic() >= st.next_at:
                    break
                live.refresh()
            st.next_at = None
            status("requesting new identity (NEWNYM)…", ui.ACCENT2)
            rotate(backend, status)


def run_lines(args, backend, history, err):
    def status(text, color=None):
        err.print(f"[dim]· {text}[/]")

    backend.on_status = status
    backend.start()
    n = 0
    while True:
        n += 1
        ident = backend.identity(n)
        history.add(ident)
        print(ui.json_line(ident) if args.json else ui.plain_line(ident), flush=True)
        if args.count and n >= args.count:
            return
        time.sleep(args.interval)
        rotate(backend, status)


def main(argv=None):
    args = parse_args(argv)
    if not args.demo and args.interval < NEWNYM_MIN:
        args.interval = NEWNYM_MIN
    log = None if (args.no_log or args.demo) else (args.log or default_log_path())
    history = History(log)
    err = Console(stderr=True, highlight=False)
    dashboard = not (args.plain or args.json) and sys.stdout.isatty()
    backend = make_backend(args, lambda msg: None)
    try:
        if dashboard:
            console = Console(highlight=False)
            st = ui.State(backend, history, None, args.interval, args.count)
            run_dashboard(args, backend, history, st, console)
        else:
            run_lines(args, backend, history, err)
    except KeyboardInterrupt:
        pass
    except TorError as e:
        err.print(f"[bold {ui.ERR}]✗[/] {e}")
        return 1
    finally:
        backend.close()
    if dashboard and history.items:
        h = history
        err.print(f"[{ui.MUTED}]nyxnet: {len(h.items)} identities · {h.unique_exits} unique exits · "
                  f"{h.countries} countries" + (f" · history in {log}" if log and h.log_path else "") + "[/]")
    return 0
