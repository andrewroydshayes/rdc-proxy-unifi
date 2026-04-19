# rdc-proxy-unifi

UniFi/EdgeSwitch port-counter plugin for [rdc-proxy](https://github.com/andrewroydshayes/rdc-proxy).

Adds a "switch" side channel to the rdc-proxy dashboard containing live port
counters polled via SSH from a UniFi/EdgeSwitch running `swctrl`.

## Prerequisites

- **rdc-proxy already installed** on the same host (it provides the plugin
  loader + dashboard).
- A UniFi/EdgeSwitch (any model supporting `swctrl port show counters`).
- An SSH key that the rdc-proxy service user can use to log into the switch.

## Install

Assuming rdc-proxy is already running at `/opt/rdc-proxy`:

```bash
# Clone and install into the rdc-proxy venv
sudo git clone https://github.com/andrewroydshayes/rdc-proxy-unifi.git /opt/rdc-proxy-unifi
sudo /opt/rdc-proxy/venv/bin/pip install /opt/rdc-proxy-unifi

# Place your SSH key where the service can read it (0600 root:root)
sudo cp ~/.ssh/id_rsa_unifi /etc/rdc-proxy/id_rsa_unifi
sudo chmod 600 /etc/rdc-proxy/id_rsa_unifi

# Configure via env vars in /etc/rdc-proxy/rdc-proxy.env (see below), then:
sudo systemctl restart rdc-proxy
```

The rdc-proxy service will log `[plugins] loaded: unifi` on startup.

Or use the included installer:

```bash
curl -fsSL https://raw.githubusercontent.com/andrewroydshayes/rdc-proxy-unifi/main/install/install-unifi.sh \
  | sudo bash
```

## Configuration

Add to `/etc/rdc-proxy/rdc-proxy.env`:

```
RDC_UNIFI_SWITCH_IP=192.168.1.97
RDC_UNIFI_SWITCH_USER=root
RDC_UNIFI_SSH_KEY=/etc/rdc-proxy/id_rsa_unifi
RDC_UNIFI_PORT_ID=9
RDC_UNIFI_POLL_INTERVAL=30
RDC_UNIFI_SIDE_CHANNEL=switch
```

All env vars have defaults — only set the ones you need to change.

## How the side channel surfaces

The plugin calls `state.update_side_channel("switch", {...counters...})` once
per poll. rdc-proxy's dashboard collector merges all side channels into the
JSON returned by `/api/status`, under `side_channels`. For UI back-compat the
"switch" channel is ALSO mirrored at the top level as `switch` in each
dashboard history point.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT.
