import json
import time

from rich.console import Console

from nyxnet import cli, ui
from nyxnet.demo import DemoBackend
from nyxnet.model import History


def test_demo_plain_runs_requested_count(capsys):
    assert cli.main(["--demo", "--plain", "-n", "3", "-i", "0", "--demo-speed", "50"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3 and all("tor ✓" in l for l in lines)


def test_demo_json_once(capsys):
    assert cli.main(["--demo", "--json", "--once", "--demo-speed", "50"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["is_tor"] is True and len(data["path"]) == 3


def test_demo_circuits_have_distinct_relays():
    b = DemoBackend(speed=1000)
    for n in range(20):
        names = [h.nickname for h in b.identity(n).path]
        assert len(set(names)) == 3


def test_interval_is_clamped_for_real_tor():
    args = cli.parse_args(["-i", "2"])
    assert args.interval == 2  # clamped in main(), not by the parser
    assert cli.NEWNYM_MIN == 10


def test_dashboard_renders_at_common_sizes():
    b = DemoBackend(speed=1000)
    h = History()
    st = ui.State(b, h, "203.0.113.42", 15, 0)
    for n in range(1, 4):
        h.add(b.identity(n))
    st.next_at = time.monotonic() + 5
    for w, hgt in ((80, 24), (112, 34), (160, 48)):
        c = Console(width=w, height=hgt, record=True, color_system=None)
        c.print(ui.render(st, (w, hgt)))
        out = c.export_text()
        assert "Rotations" in out and "203.•••.•••.42" in out and "203.0.113.42" not in out
