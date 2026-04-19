"""rdc-proxy-unifi: UniFi/EdgeSwitch port-counter plugin for rdc-proxy.

Spawns a background thread that SSHes to a UniFi switch and polls the
"swctrl port show counters id <N>" command, then pushes parsed counters
into the rdc-proxy state as a side channel named "switch" (for UI
back-compat with the original embedded collector).

All configuration is via environment variables so nothing sensitive lives
in code:

  RDC_UNIFI_SWITCH_IP      Switch management IP (default 10.0.0.97)
  RDC_UNIFI_SWITCH_USER    SSH user (default root)
  RDC_UNIFI_SSH_KEY        Path to SSH private key
                           (default /etc/rdc-proxy/id_rsa_unifi)
  RDC_UNIFI_PORT_ID        Port number to poll (default 9)
  RDC_UNIFI_POLL_INTERVAL  Seconds between polls (default 30)
  RDC_UNIFI_SIDE_CHANNEL   Side-channel name (default "switch")
"""

from rdc_proxy_unifi.poll import Plugin  # noqa: F401

__version__ = "0.2.0"
