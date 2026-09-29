#!/usr/bin/env bash
# usage: verify_manifest.sh <research/structural_arb dir> <MANIFEST> <structural_deploy dir> <DEPLOY_MANIFEST>
# MANIFEST        = sha256 of `sha256sum` lines (LC_ALL=C sorted by path) of every git-tracked file under
#                   research/structural_arb except data/ and relabels/  (STRUCTURAL_FREEZE_HASHES.txt)
# DEPLOY_MANIFEST = the same over every git-tracked file under this deploy directory (DEPLOY_HASHES.txt)
set -euo pipefail
h(){ (cd "$1" && git ls-files | { grep -v '^data/\|^relabels/' || true; } | LC_ALL=C sort | tr '\n' '\0' | xargs -0 -r sha256sum | LC_ALL=C sort -k2 | sha256sum | cut -d' ' -f1); }
got=$(h "$1"); [ "$got" = "$2" ] || { echo "EXPERIMENT MANIFEST MISMATCH: $got != $2"; exit 1; }
got=$(h "$3"); [ "$got" = "$4" ] || { echo "DEPLOY MANIFEST MISMATCH: $got != $4"; exit 1; }
echo "MANIFESTS OK $2 $4"
