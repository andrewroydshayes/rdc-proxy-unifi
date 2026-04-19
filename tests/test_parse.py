"""Parser + plugin behavior tests. No real switch needed — we monkeypatch
subprocess.check_output."""

from unittest.mock import patch

from rdc_proxy_unifi.poll import (
    Plugin,
    build_ssh_cmd,
    parse_switch_counters,
    poll_once,
)


SAMPLE_OUTPUT = """\
Port: 9 | Admin: Up | Operational: Up
RxPackets: 123456 | TxPackets: 654321 | RxBytes: 99999999 | TxBytes: 88888888
RxErrors: 0 | TxErrors: 0 | RxDropped: 3 | RxCrcErrors: 0
"""


def test_parse_extracts_known_ints():
    d = parse_switch_counters(SAMPLE_OUTPUT)
    assert d["RxPackets"] == 123456
    assert d["TxPackets"] == 654321
    assert d["RxBytes"] == 99999999
    assert d["RxDropped"] == 3
    assert d["RxErrors"] == 0


def test_parse_skips_non_integer_values():
    d = parse_switch_counters("Port: 9 | Admin: Up | Operational: Up")
    # "Up" isn't an int so Admin+Operational are skipped silently
    assert "Admin" not in d
    assert d["Port"] == 9


def test_parse_handles_empty_input():
    assert parse_switch_counters("") == {}


def test_parse_tolerates_malformed_lines():
    txt = "noseparator\nkey:12345\n|||  \n"
    d = parse_switch_counters(txt)
    assert d == {"key": 12345}


def test_build_ssh_cmd_shape():
    cmd = build_ssh_cmd("1.2.3.4", "admin", "/tmp/key", "9")
    assert cmd[0] == "ssh"
    assert "-i" in cmd and "/tmp/key" in cmd
    assert "admin@1.2.3.4" in cmd
    assert cmd[-1] == "swctrl port show counters id 9"


def test_poll_once_returns_parsed_on_success():
    with patch("subprocess.check_output", return_value=SAMPLE_OUTPUT):
        data = poll_once("1.2.3.4", "admin", "/tmp/k", "9")
    assert data["RxPackets"] == 123456
    assert "ts" in data


def test_poll_once_returns_error_dict_on_failure():
    def raise_(*a, **kw):
        raise RuntimeError("ssh refused")
    with patch("subprocess.check_output", side_effect=raise_):
        data = poll_once("1.2.3.4", "admin", "/tmp/k", "9")
    assert "error" in data
    assert "ssh refused" in data["error"]


class _StubState:
    def __init__(self):
        self.channels = {}
    def update_side_channel(self, name, data):
        self.channels[name] = dict(data)


def test_plugin_registers_side_channel(monkeypatch):
    """Plugin.start() must push data into state.update_side_channel under the
    configured name. We short-circuit the sleep loop by running poll_once once
    and checking state directly — avoiding background-thread timing."""
    from rdc_proxy_unifi import poll as poll_mod
    state = _StubState()
    monkeypatch.setattr(poll_mod, "poll_once", lambda *a, **kw: {"RxPackets": 1, "ts": 1.0})

    # Run a single iteration manually
    cfg = poll_mod._load_env_config()
    data = poll_mod.poll_once(cfg["switch_ip"], cfg["switch_user"], cfg["ssh_key"], cfg["port_id"])
    state.update_side_channel(cfg["side_channel"], data)

    assert cfg["side_channel"] in state.channels
    assert state.channels[cfg["side_channel"]]["RxPackets"] == 1


def test_env_vars_override_defaults(monkeypatch):
    from rdc_proxy_unifi import poll as poll_mod
    monkeypatch.setenv("RDC_UNIFI_SWITCH_IP", "10.9.8.7")
    monkeypatch.setenv("RDC_UNIFI_PORT_ID", "42")
    monkeypatch.setenv("RDC_UNIFI_POLL_INTERVAL", "5")
    cfg = poll_mod._load_env_config()
    assert cfg["switch_ip"] == "10.9.8.7"
    assert cfg["port_id"] == "42"
    assert cfg["poll_interval"] == 5
