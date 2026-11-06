from datetime import datetime

from nyxnet.model import History, Identity, country_name, mask_ip


def ident(n, ip, cc="DE", lat=1000):
    return Identity(n=n, at=datetime(2026, 1, 1), exit_ip=ip, country=cc, is_tor=True, latency_ms=lat)


def test_mask_ipv4_keeps_only_first_and_last_octet():
    assert mask_ip("203.0.113.42") == "203.•••.•••.42"


def test_mask_ipv6_and_garbage():
    assert mask_ip("2001:db8::1") == "2001:•••:•••"
    assert mask_ip("not-an-ip") == "•••"
    assert mask_ip(None) == "—"


def test_country_name():
    assert country_name("de") == "Germany"
    assert country_name("??") == "unknown"
    assert country_name("ZZ") == "ZZ"


def test_history_stats_and_reuse():
    h = History()
    h.add(ident(1, "192.0.2.1", "DE", 1000))
    h.add(ident(2, "192.0.2.2", "NL", 2000))
    h.add(ident(3, "192.0.2.1", "DE", 3000))
    assert [i.reused for i in h.items] == [False, False, True]
    assert h.unique_exits == 2
    assert h.countries == 2
    assert h.avg_latency == 2000


def test_failed_identity_is_not_counted():
    h = History()
    h.add(Identity(n=1, at=datetime(2026, 1, 1), error="ConnectTimeout"))
    assert h.unique_exits == 0 and h.avg_latency is None


def test_history_log_is_jsonl(tmp_path):
    log = tmp_path / "sub" / "history.jsonl"
    h = History(log)
    h.add(ident(1, "192.0.2.1"))
    h.add(ident(2, "192.0.2.2"))
    lines = log.read_text().splitlines()
    assert len(lines) == 2 and '"exit_ip": "192.0.2.2"' in lines[1]
