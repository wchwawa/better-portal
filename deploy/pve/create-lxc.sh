#!/usr/bin/env bash
# create-lxc.sh - run the automatic relay in an Alpine LXC on Proxmox VE.
#
# Run as root in the PVE host shell, from a checkout or extracted release of this repo.
# Creates (or updates) a small unprivileged Alpine container bridged onto your LAN and
# installs the relay from this checkout with an OpenRC service. The service is NOT
# enabled until you have run configure -> baseline -> try inside the container.
#
#   bash deploy/pve/create-lxc.sh
#   CTID=215 NET_IP=192.168.1.215/24 GATEWAY=192.168.1.1 bash deploy/pve/create-lxc.sh
#   CTID=215 bash deploy/pve/create-lxc.sh      # existing CT: update the relay inside it
set -euo pipefail

CTID="${CTID:-}"
CT_HOSTNAME="${CT_HOSTNAME:-portal-relay}"
BRIDGE="${BRIDGE:-vmbr0}"          # the bridge on the same LAN as the PS5 and Portal
VLAN="${VLAN:-}"                   # only if that LAN is a tagged VLAN on the bridge
NET_IP="${NET_IP:-dhcp}"           # or e.g. 192.168.1.215/24 (then set GATEWAY too)
GATEWAY="${GATEWAY:-}"
ROOTFS_STORAGE="${ROOTFS_STORAGE:-}"   # auto: local-lvm if present, else first rootdir storage
TEMPLATE_STORAGE="${TEMPLATE_STORAGE:-local}"
CORES="${CORES:-1}"
MEMORY="${MEMORY:-384}"            # relay + guardian: two ~70 MB Python processes (~180 MB used)
SWAP="${SWAP:-256}"
DISK_GB="${DISK_GB:-2}"

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" = 0 ] || die "Run as root on the Proxmox host."
command -v pct >/dev/null && command -v pveam >/dev/null || die "pct/pveam not found - run this on the PVE host."
ip link show "$BRIDGE" >/dev/null 2>&1 || die "Bridge $BRIDGE not found (ip -br link | grep vmbr)."

# ------------------------------------------------------------ source files
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
FILES=(portal_active_probe.py portal_auto.py portal_auto_platform.py portal_capture.py
       portal_egress_witness.py portal_windows.py portal_windows_network.py protocol.py
       portal_recovery.py portal_tui.py portal_tui_text.py portal_tui_platform.py portal_windows_launcher.py portal_cli.py
       locales/zh-CN.json locales/ja.json locales/ko.json locales/es.json locales/fr.json
       requirements.txt LICENSE deploy/install-alpine.sh deploy/portal deploy/portal-bitrate.initd)
for f in "${FILES[@]}"; do [ -f "$ROOT/$f" ] || die "$ROOT/$f missing - run from a complete checkout."; done
REV=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || basename "$ROOT")
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
(cd "$ROOT" && tar -czf "$WORK/portal-src.tgz" "${FILES[@]}" tests/*.py)

# ------------------------------------------------------------ container
if [ -n "$CTID" ] && pct status "$CTID" >/dev/null 2>&1; then
  say "CT $CTID exists - updating the relay inside it."
  pct config "$CTID" | grep -q '^ostype: alpine' || die "CT $CTID is not Alpine; pick another CTID."
  if pct config "$CTID" | grep -E '^net0:' | grep -q 'firewall=1'; then
    warn "CT $CTID net0 has firewall=1. PVE's IP/ARP filter can drop the relay's frames; set firewall=0 on net0."
  fi
  [ "$(pct status "$CTID" | awk '{print $2}')" = running ] || pct start "$CTID"
else
  CTID="${CTID:-$(pvesh get /cluster/nextid)}"
  if [ -z "$ROOTFS_STORAGE" ]; then
    STORES=$(pvesm status --content rootdir 2>/dev/null | awk 'NR>1 && $3=="active"{print $1}')
    if echo "$STORES" | grep -qx local-lvm; then ROOTFS_STORAGE=local-lvm
    else ROOTFS_STORAGE=$(echo "$STORES" | head -1); fi
  fi
  [ -n "$ROOTFS_STORAGE" ] || die "No active storage with 'rootdir' content; set ROOTFS_STORAGE."

  say "Finding the newest Alpine amd64 template"
  pveam update >/dev/null 2>&1 || warn "pveam update failed; using the cached template index."
  NAME=$(pveam available --section system | awk '{print $2}' |
         grep -E '^alpine-3\.[0-9]+-default_[0-9]+_amd64\.tar\.(xz|gz|zst)$' | sort -V | tail -1)
  [ -n "$NAME" ] || die "No Alpine amd64 template in 'pveam available'."
  TPL="$TEMPLATE_STORAGE:vztmpl/$NAME"
  pveam list "$TEMPLATE_STORAGE" | awk '{print $1}' | grep -qx "$TPL" || pveam download "$TEMPLATE_STORAGE" "$NAME"

  # firewall=0: PVE's ipfilter would drop the relay's ARP replies for the PS5's address.
  NET0="name=eth0,bridge=$BRIDGE,ip=$NET_IP,firewall=0${GATEWAY:+,gw=$GATEWAY}${VLAN:+,tag=$VLAN}"
  say "Creating CT $CTID ($CT_HOSTNAME) from $NAME on $ROOTFS_STORAGE, net0: $NET0"
  pct create "$CTID" "$TPL" \
    --hostname "$CT_HOSTNAME" --ostype alpine --unprivileged 1 \
    --cores "$CORES" --memory "$MEMORY" --swap "$SWAP" \
    --rootfs "$ROOTFS_STORAGE:$DISK_GB" --net0 "$NET0" \
    --onboot 1 --tags portal \
    --description "PS Portal bitrate relay (ps5-portal-high-bitrate auto mode, $REV). Inside: 'portal help'. Keep firewall=0 and no Docker in this CT (needs ip_forward=0)."
  pct start "$CTID"
fi

say "Waiting for CT $CTID to get an IPv4 address"
CT_IP=""
for _ in $(seq 1 30); do
  CT_IP=$(pct exec "$CTID" -- ip -4 addr show dev eth0 2>/dev/null | awk '/inet /{print $2; exit}' || true)
  [ -n "$CT_IP" ] && break; sleep 2
done
[ -n "$CT_IP" ] || die "CT $CTID has no IPv4 on eth0. Check the bridge/VLAN and DHCP."
say "CT $CTID is at $CT_IP"

# ------------------------------------------------------------ install inside
say "Installing the relay ($REV) in CT $CTID"
pct push "$CTID" "$WORK/portal-src.tgz" /root/portal-src.tgz
pct exec "$CTID" -- sh -c 'rm -rf /root/portal-src && mkdir /root/portal-src && tar xzf /root/portal-src.tgz -C /root/portal-src'
pct exec "$CTID" -- env PORTAL_SOURCE_REV="$REV" sh /root/portal-src/deploy/install-alpine.sh
pct exec "$CTID" -- rm -rf /root/portal-src /root/portal-src.tgz

cat <<EOF

Done. CT $CTID ($CT_HOSTNAME) at $CT_IP. The service is installed but not enabled yet.
(PVE host ip_forward=$(cat /proc/sys/net/ipv4/ip_forward); the container keeps its own at 0.)

Next, from this shell:
  pct enter $CTID
  portal configure 65     # PS5 + Portal awake; interface: eth0; enter both IPs
  portal baseline         # disconnect Portal first; connect after BASELINE READY; check 60 s
  portal try              # connect after AUTO READY; check the Portal's network info; Ctrl+C
  portal enable           # only if 'try' looked good: starts now and at every boot
EOF
