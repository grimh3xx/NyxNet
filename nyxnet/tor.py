"""Talks to Tor: attaches to a running instance through its ControlPort, or launches a
private one (temporary data directory, random ports) so no torrc editing or root is needed.
"""
import re
import shutil
import socket
import tempfile
import threading
import time
from datetime import datetime

import requests
import stem
import stem.process
from stem import Signal
from stem.control import Controller, EventType
from stem.response.events import StreamEvent

from .model import Hop, Identity, TorError

CHECK_URL = "https://check.torproject.org/api/ip"
CHECK_HOST = "check.torproject.org"
REAL_IP_URL = "https://api.ipify.org"


def free_port(preferred=0):
    """`preferred` if it is free (so browsers can keep a fixed proxy setting), else any free port."""
    for port in (preferred, 0) if preferred else (0,):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return s.getsockname()[1]


def real_ip(timeout=10):
    """Public IP without Tor. Only ever shown masked."""
    try:
        return requests.get(REAL_IP_URL, timeout=timeout).text.strip() or None
    except requests.RequestException:
        return None


class TorBackend:
    name = "tor"

    def __init__(self, socks_port=9050, control_port=9051, password=None, launch="auto",
                 tor_cmd="tor", timeout=20, on_status=None):
        self.socks_port, self.control_port = socks_port, control_port
        self.password, self.launch, self.tor_cmd, self.timeout = password, launch, tor_cmd, timeout
        self.on_status = on_status or (lambda msg: None)
        self.attempts = 3
        self.controller = None
        self.process = None
        self.datadir = None
        self.mode = None   # "attached" or "launched"

    # ------------------------------------------------------------- lifecycle
    def start(self):
        if self.launch != "always":
            try:
                self._attach(self.control_port)
                self.mode = "attached"
                return
            except TorError:
                if self.launch == "never":
                    raise
        self._launch()
        self.mode = "launched"

    def _attach(self, port):
        try:
            c = Controller.from_port(port=port)
        except stem.SocketError as e:
            raise TorError(f"no Tor ControlPort on 127.0.0.1:{port} ({e})") from None
        try:
            c.authenticate(password=self.password)
        except stem.connection.AuthenticationFailure as e:
            c.close()
            raise TorError(f"ControlPort {port} refused authentication: {e}") from None
        self.controller = c

    def _launch(self):
        if not shutil.which(self.tor_cmd):
            raise TorError("the 'tor' binary was not found. Install it (e.g. `sudo pacman -S tor`, "
                           "`sudo apt install tor`, `brew install tor`) or point --tor-cmd at it")
        self.datadir = tempfile.mkdtemp(prefix="nyxnet-")
        self.socks_port, self.control_port = free_port(self.socks_port), free_port(self.control_port)
        self.on_status("starting a private Tor instance")

        last = []

        def progress(line):
            m = re.search(r"Bootstrapped (\d+)%[^:]*: (.*)", line)
            if m and m.group(1) not in last:  # tor logs each step twice (stdout + notice log)
                last.append(m.group(1))
                self.on_status(f"bootstrapping Tor {m.group(1)}% · {m.group(2).lower()}")

        try:
            self.process = stem.process.launch_tor_with_config(
                tor_cmd=self.tor_cmd, take_ownership=True, timeout=None, init_msg_handler=progress,
                config={"SocksPort": str(self.socks_port), "ControlPort": str(self.control_port),
                        "DataDirectory": self.datadir, "CookieAuthentication": "1",
                        "AvoidDiskWrites": "1"},
            )
        except OSError as e:
            raise TorError(f"Tor failed to start: {e}") from None
        self._attach(self.control_port)

    def close(self):
        if self.controller:
            self.controller.close()
        if self.process:
            self.process.kill()
            self.process.wait()
        if self.datadir:
            shutil.rmtree(self.datadir, ignore_errors=True)

    @property
    def socks(self):
        return f"127.0.0.1:{self.socks_port}"

    # ------------------------------------------------------------- identity
    def newnym_wait(self):
        """Seconds until Tor accepts another NEWNYM (it rate-limits them to one every ~10 s)."""
        return 0.0 if self.controller.is_newnym_available() else self.controller.get_newnym_wait()

    def newnym(self):
        wait = self.newnym_wait()
        if wait > 0:
            time.sleep(wait)
        self.controller.signal(Signal.NEWNYM)

    def identity(self, n):
        """Fetch the current exit through Tor and resolve the circuit that carried it."""
        ident = Identity(n=n, at=datetime.now())
        circ, ours = {}, set()
        done = threading.Event()

        def on_stream(ev: StreamEvent):
            # Tor REMAPs the hostname to an IP before SUCCEEDED, so follow the stream id
            if ev.target_address == CHECK_HOST:
                ours.add(ev.id)
            if ev.id in ours and ev.status == "SUCCEEDED" and ev.circ_id:
                circ["id"] = ev.circ_id
                done.set()

        self.controller.add_event_listener(on_stream, EventType.STREAM)
        proxy = f"socks5h://127.0.0.1:{self.socks_port}"
        try:
            for attempt in range(self.attempts):  # a fresh circuit sometimes drops the first TLS handshake
                circ.clear()
                done.clear()
                try:
                    t0 = time.monotonic()
                    r = requests.get(CHECK_URL, proxies={"http": proxy, "https": proxy}, timeout=self.timeout)
                    ident.latency_ms = round((time.monotonic() - t0) * 1000)
                    data = r.json()
                    ident.exit_ip, ident.is_tor, ident.error = data.get("IP"), bool(data.get("IsTor")), None
                    break
                except (requests.RequestException, ValueError) as e:
                    ident.error = type(e).__name__
        finally:
            done.wait(1.0)
            self.controller.remove_event_listener(on_stream)

        if ident.exit_ip:
            ident.country = self._country(ident.exit_ip)
        if "id" in circ:
            ident.path = self._path(circ["id"])
        return ident

    def _country(self, ip):
        try:
            return self.controller.get_info(f"ip-to-country/{ip}").upper()
        except (stem.ControllerError, ValueError):
            return "??"

    def _path(self, circ_id):
        try:
            circuit = self.controller.get_circuit(circ_id)
        except (stem.ControllerError, ValueError):
            return []
        hops = []
        last = len(circuit.path) - 1
        for i, (fp, nick) in enumerate(circuit.path):
            role = "guard" if i == 0 else "exit" if i == last else "middle"
            hop = Hop(role=role, nickname=nick or fp[:8], fingerprint=fp)
            try:
                hop.address = self.controller.get_network_status(fp).address
                hop.country = self._country(hop.address)
            except (stem.ControllerError, ValueError):
                pass
            hops.append(hop)
        return hops
