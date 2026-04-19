"""Background poll loop for UniFi/EdgeSwitch port counters over SSH."""

import os
import subprocess
import threading
import time


DEFAULT_SWITCH_IP = "10.0.0.97"
DEFAULT_SWITCH_USER = "root"
DEFAULT_SSH_KEY = "/etc/rdc-proxy/id_rsa_unifi"
DEFAULT_PORT_ID = "9"
DEFAULT_POLL_INTERVAL = 30
DEFAULT_SIDE_CHANNEL = "switch"


def parse_switch_counters(text):
    """Parse `swctrl port show counters id N` output into a flat dict of
    ints. Lines are pipe-delimited key:value pairs."""
    out = {}
    for line in text.strip().split("\n"):
        for part in line.split("|"):
            part = part.strip()
            if ":" not in part:
                continue
            key, val = part.rsplit(":", 1)
            try:
                out[key.strip()] = int(val.strip())
            except ValueError:
                pass
    return out


def build_ssh_cmd(switch_ip, switch_user, ssh_key, port_id):
    return [
        "ssh",
        "-i", ssh_key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5",
        "-o", "PubkeyAcceptedAlgorithms=+ssh-rsa",
        "-o", "HostkeyAlgorithms=+ssh-rsa",
        f"{switch_user}@{switch_ip}",
        f"swctrl port show counters id {port_id}",
    ]


def poll_once(switch_ip, switch_user, ssh_key, port_id, timeout=10):
    """Run one SSH+parse. Returns a dict (possibly empty on failure)."""
    cmd = build_ssh_cmd(switch_ip, switch_user, ssh_key, port_id)
    try:
        raw = subprocess.check_output(
            cmd, text=True, timeout=timeout, stderr=subprocess.DEVNULL
        )
        data = parse_switch_counters(raw)
        data["ts"] = time.time()
        return data
    except Exception as e:
        return {"error": str(e), "ts": time.time()}


def run_poll_loop(state, cfg):
    while True:
        data = poll_once(
            cfg["switch_ip"], cfg["switch_user"], cfg["ssh_key"], cfg["port_id"]
        )
        state.update_side_channel(cfg["side_channel"], data)
        time.sleep(cfg["poll_interval"])


def _load_env_config():
    return {
        "switch_ip": os.environ.get("RDC_UNIFI_SWITCH_IP", DEFAULT_SWITCH_IP),
        "switch_user": os.environ.get("RDC_UNIFI_SWITCH_USER", DEFAULT_SWITCH_USER),
        "ssh_key": os.environ.get("RDC_UNIFI_SSH_KEY", DEFAULT_SSH_KEY),
        "port_id": os.environ.get("RDC_UNIFI_PORT_ID", DEFAULT_PORT_ID),
        "poll_interval": int(os.environ.get("RDC_UNIFI_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)),
        "side_channel": os.environ.get("RDC_UNIFI_SIDE_CHANNEL", DEFAULT_SIDE_CHANNEL),
    }


class Plugin:
    """Entry-point class. rdc-proxy instantiates with no args, then calls start(state)."""

    name = "unifi"

    def start(self, state):
        cfg = _load_env_config()
        print(
            f"[unifi] polling {cfg['switch_user']}@{cfg['switch_ip']} port {cfg['port_id']} "
            f"every {cfg['poll_interval']}s -> side_channel '{cfg['side_channel']}'",
            flush=True,
        )
        t = threading.Thread(
            target=run_poll_loop,
            args=(state, cfg),
            daemon=True,
            name="unifi-poll",
        )
        t.start()
