#!/usr/bin/env bash
# Installer for rdc-proxy-unifi (UniFi port-counter plugin).
# Assumes rdc-proxy is already installed at /opt/rdc-proxy.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/andrewroydshayes/rdc-proxy-unifi/main/install/install-unifi.sh \
#     | sudo GITHUB_OWNER=<owner> bash

set -euo pipefail

GITHUB_OWNER=${GITHUB_OWNER:-andrewroydshayes}
REPO_URL=${REPO_URL:-https://github.com/${GITHUB_OWNER}/rdc-proxy-unifi.git}
INSTALL_DIR=${INSTALL_DIR:-/opt/rdc-proxy-unifi}
RDC_PROXY_DIR=${RDC_PROXY_DIR:-/opt/rdc-proxy}
RDC_PROXY_CONFIG=${RDC_PROXY_CONFIG:-/etc/rdc-proxy}
BRANCH=${BRANCH:-}

if [[ -t 1 ]]; then
  G=$(printf '\033[32m'); R=$(printf '\033[31m'); Y=$(printf '\033[33m'); N=$(printf '\033[0m')
else
  G=""; R=""; Y=""; N=""
fi

PASS=(); FAIL=(); WARN=()
ok() { PASS+=("$1"); echo "${G}✓${N} $1"; }
fail() { FAIL+=("$1"); echo "${R}✗${N} $1"; }
warn() { WARN+=("$1"); echo "${Y}!${N} $1"; }
step() { echo; echo "${G}── $1 ──${N}"; }

step "1/4  prerequisites"
[[ $EUID -ne 0 ]] && { fail "must run as root (sudo)"; exit 1; }
ok "running as root"

if [[ ! -x "$RDC_PROXY_DIR/venv/bin/pip" ]]; then
  fail "rdc-proxy venv not found at $RDC_PROXY_DIR/venv — install rdc-proxy first"
  exit 1
fi
ok "found rdc-proxy venv at $RDC_PROXY_DIR/venv"

if ! systemctl is-active --quiet rdc-proxy; then
  warn "rdc-proxy.service not currently active (will enable after install)"
else
  ok "rdc-proxy.service is active"
fi

step "2/4  fetch plugin"
if [[ -d "$INSTALL_DIR/.git" ]]; then
  git -C "$INSTALL_DIR" fetch --tags --quiet
  ok "repo present, fetched latest"
else
  git clone --quiet "$REPO_URL" "$INSTALL_DIR"
  ok "cloned $REPO_URL"
fi

if [[ -n "$BRANCH" ]]; then
  git -C "$INSTALL_DIR" checkout --quiet "$BRANCH"
  ok "checked out $BRANCH"
else
  LATEST=$(git -C "$INSTALL_DIR" tag --sort=-v:refname | head -1)
  if [[ -n "$LATEST" ]]; then
    git -C "$INSTALL_DIR" checkout --quiet "$LATEST"
    ok "checked out latest tag: $LATEST"
  else
    git -C "$INSTALL_DIR" checkout --quiet main
    warn "no tags yet — on main"
  fi
fi

step "3/4  install into rdc-proxy venv"
"$RDC_PROXY_DIR/venv/bin/pip" install --quiet "$INSTALL_DIR"
ok "pip install done"

step "4/4  restart + verify"
systemctl restart rdc-proxy
sleep 3

if journalctl -u rdc-proxy --since "10 seconds ago" --no-pager 2>/dev/null | grep -q "plugins.*loaded.*unifi"; then
  ok "plugin loaded at runtime (saw '[plugins] loaded: unifi')"
else
  warn "didn't see plugin-loaded log yet — check 'journalctl -u rdc-proxy -f'"
fi

if systemctl is-active --quiet rdc-proxy; then
  ok "rdc-proxy.service active after restart"
else
  fail "rdc-proxy.service not active after restart"
fi

echo
echo "── Summary ──"
echo "${G}Passed (${#PASS[@]}):${N}"; printf '  ✓ %s\n' "${PASS[@]}"
[[ ${#WARN[@]} -gt 0 ]] && { echo "${Y}Warnings (${#WARN[@]}):${N}"; printf '  ! %s\n' "${WARN[@]}"; }
if [[ ${#FAIL[@]} -gt 0 ]]; then
  echo "${R}Failed (${#FAIL[@]}):${N}"; printf '  ✗ %s\n' "${FAIL[@]}"
  exit 1
fi

echo
echo "${G}rdc-proxy-unifi installed.${N}"
echo
echo "Next steps:"
echo "  1. Place your switch SSH key:  sudo cp ~/.ssh/id_rsa_unifi $RDC_PROXY_CONFIG/"
echo "  2. Chmod:                       sudo chmod 600 $RDC_PROXY_CONFIG/id_rsa_unifi"
echo "  3. Configure (append to $RDC_PROXY_CONFIG/rdc-proxy.env):"
echo "       RDC_UNIFI_SWITCH_IP=..."
echo "       RDC_UNIFI_PORT_ID=..."
echo "  4. sudo systemctl restart rdc-proxy"
