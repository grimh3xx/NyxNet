"""Simulated Tor network for --demo: lets you try the dashboard without Tor or a network.

Every address comes from the documentation ranges (RFC 5737) and every relay name is
made up, so recordings never show a real IP or a real relay.
"""
import random
import time
from datetime import datetime

from .model import Hop, Identity

NICKS = ["quietmoth", "ArcticFern", "relaybox07", "nightjar", "CopperLark", "fogbank", "Hallonbit",
         "tidepool", "OrbitMint", "stillwater", "Kestrel42", "lanternfly", "marblecat", "NordicAsh",
         "paperkite", "Vantablack", "willowisp", "zeroday0", "cobaltreef", "duskhollow"]
COUNTRIES = ["DE", "NL", "FR", "SE", "CH", "US", "FI", "RO", "AT", "NO", "LU", "CA", "IS", "PL"]
RANGES = ["192.0.2.", "198.51.100."]


class DemoBackend:
    name = "demo"
    mode = "demo"
    socks = "127.0.0.1:9050"

    def __init__(self, seed=7, speed=1.0, on_status=None):
        self.rng = random.Random(seed)
        self.speed = speed
        self.on_status = on_status or (lambda msg: None)
        self.guard = self._relay("guard")

    def _relay(self, role, taken=()):
        ip = self.rng.choice(RANGES) + str(self.rng.randint(2, 254))
        return Hop(role=role, nickname=self.rng.choice([n for n in NICKS if n not in taken]),
                   fingerprint="".join(self.rng.choice("0123456789ABCDEF") for _ in range(40)),
                   address=ip, country=self.rng.choice(COUNTRIES))

    def start(self):
        for pct, step in ((0, "starting"), (25, "requesting status"), (50, "loading descriptors"),
                          (75, "establishing circuit"), (100, "done")):
            self.on_status(f"bootstrapping Tor {pct}% · {step}")
            time.sleep(0.25 / self.speed)

    def close(self):
        pass

    def newnym_wait(self):
        return 0.0

    def newnym(self):
        time.sleep(0.3 / self.speed)

    def identity(self, n):
        time.sleep(self.rng.uniform(0.3, 0.7) / self.speed)
        middle = self._relay("middle", {self.guard.nickname})
        exit_ = self._relay("exit", {self.guard.nickname, middle.nickname})
        path = [self.guard, middle, exit_]  # the guard stays fixed, like real Tor
        return Identity(n=n, at=datetime.now(), exit_ip=exit_.address, country=exit_.country,
                        is_tor=True, latency_ms=self.rng.randint(900, 3800), path=path)


def demo_real_ip():
    return "203.0.113.42"  # kept outside the relay ranges
