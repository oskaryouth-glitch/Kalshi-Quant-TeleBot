#!/usr/bin/env bash
# Install the M6 collector ISOLATED from H038/H039. Does NOT enable or start anything.
# usage (as root, from a checkout of the repo at the frozen commit): ./install.sh <FROZEN_MANIFEST_SHA256>
set -euo pipefail
MANIFEST="$1"
SRC="$(cd "$(dirname "$0")/../.." && pwd)"          # research/edge_search
id m6paper >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin m6paper
REL=/opt/m6_paper/releases/$MANIFEST
install -d -o root -g root -m 0755 "$REL"
cp -a "$SRC/m6_paper" "$REL/"
cp -a "$SRC/price_test_1" "$REL/" 2>/dev/null || true     # tests compare lip.py with the PT1-frozen functions
cd "$REL" && python3 -m m6_paper.prereg --verify "$MANIFEST"      # refuse to install code that is not the frozen code
echo "$MANIFEST" > "$REL/MANIFEST"; echo "M6_MANIFEST=$MANIFEST" > "$REL/manifest.env"
chown -R root:root "$REL"; chmod -R go-w "$REL"
ln -sfn "$REL" /opt/m6_paper/current
install -d -o m6paper -g m6paper -m 0750 /srv/m6_paper /srv/m6_paper/data /srv/m6_paper/validation /srv/m6_paper/logs /srv/m6_paper/quarantine
rm -f /srv/m6_paper/APPROVED                                       # written only after final reviewer approval
install -m 0644 "$REL/m6_paper/deploy/m6-paper-collector.service" /etc/systemd/system/m6-paper-collector.service
systemctl daemon-reload
systemctl disable m6-paper-collector.service 2>/dev/null || true
echo "installed $MANIFEST (disabled; not started)"
