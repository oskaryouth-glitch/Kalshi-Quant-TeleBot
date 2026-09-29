#!/usr/bin/env bash
# Install the structural_arb collector on the dedicated host. Does NOT enable or start anything.
# usage (as root, from a checkout of the repo that contains the frozen commit):
#   ./install.sh <FROZEN_COMMIT> <FROZEN_CONFIG_VERSION> <FROZEN_MANIFEST_SHA256> <DEPLOY_MANIFEST_SHA256>
# Refuses unless the experiment files at the commit hash to the frozen manifest, the deploy files hash to the
# deploy manifest, and config.py carries the frozen CONFIG_VERSION.
set -euo pipefail
COMMIT="$1"; CFG="$2"; MANIFEST="$3"; DEPLOY="$4"
SRC="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
REL=/opt/sarb/releases/$MANIFEST
[ ! -e "$REL" ] || { echo "release already exists: $REL"; exit 1; }
id sarb >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin sarb
install -d -o root -g root -m 0755 /opt/sarb/releases "$REL"
git clone --quiet --no-hardlinks "$SRC" "$REL/repo"
git -C "$REL/repo" checkout --quiet --detach "$COMMIT"
EXP="$REL/repo/research/structural_arb"; DEP="$REL/repo/research/edge_search/proposals/structural_deploy"
"$DEP/verify_manifest.sh" "$EXP" "$MANIFEST" "$DEP" "$DEPLOY"
grep -q "^CONFIG_VERSION = \"$CFG\"$" "$EXP/sarb/config.py" || { echo "CONFIG_VERSION mismatch"; exit 1; }
[ -z "$(git -C "$EXP" status --porcelain -- .)" ] || { echo "experiment tree not clean"; exit 1; }
printf 'SARB_COMMIT=%s\nSARB_CONFIG_VERSION=%s\nSARB_MANIFEST=%s\nSARB_DEPLOY_MANIFEST=%s\n' "$COMMIT" "$CFG" "$MANIFEST" "$DEPLOY" > "$REL/release.env"
chown -R root:root "$REL"; chmod -R go-w "$REL"
ln -sfn "$REL" /opt/sarb/current
install -d -o sarb -g sarb -m 0750 /srv/sarb /srv/sarb/data /srv/sarb/validation /srv/sarb/logs /srv/sarb/quarantine
rm -f /srv/sarb/APPROVED /srv/sarb/WINDOW                          # written only by start.sh after final approval
install -m 0644 "$DEP/sarb-collector.service" /etc/systemd/system/sarb-collector.service
systemctl daemon-reload
systemctl disable sarb-collector.service 2>/dev/null || true
echo "installed commit $COMMIT manifest $MANIFEST deploy $DEPLOY (disabled; not started)"
