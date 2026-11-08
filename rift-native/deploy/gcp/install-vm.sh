#!/usr/bin/env bash
# Run on the dedicated Ubuntu 24.04 GCP VM as a sudo-capable user.
# REF=main DOMAIN=lol.lcktcg.com bash install-vm.sh
set -euo pipefail
REF="${REF:-main}"
DOMAIN="${DOMAIN:-lol.lcktcg.com}"
APP_ROOT="/opt/rift-manager"
DATA_ROOT="/var/lib/rift-manager"
REPO="https://github.com/suni211/LFM.git"
REQUIRE_VERIFIED="${REQUIRE_VERIFIED:-1}"
if [[ "$EUID" -eq 0 ]]; then
  echo 'Run as the ordinary SSH user with sudo access, not as root.' >&2
  exit 1
fi
case "$DOMAIN" in lol.lcktcg.com) ;; *) echo "Unexpected domain; aborting" >&2; exit 1;; esac
command -v sudo >/dev/null || { echo 'sudo is required' >&2; exit 1; }
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl git rsync sqlite3 python3 python3-venv python3-pip caddy
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git clone --depth=1 --filter=blob:none --sparse --branch="$REF" "$REPO" "$tmp/repo"
git -C "$tmp/repo" sparse-checkout set \
  rift-native/server rift-native/engine rift-native/web rift-native/assets
src="$tmp/repo/rift-native"
# Production is deliberately blocked until EVERY real record has a verified ISO code.
python3 - "$src/assets/people.json" "$REQUIRE_VERIFIED" <<'PY'
import json,sys
people=json.load(open(sys.argv[1],encoding='utf-8'))['people']
missing=[p for p in people if p.get('real_person') and not p.get('nationality_code')]
print('Registered people:',len(people),'Missing verified nationality codes:',len(missing))
if missing and sys.argv[2]=='1':
    raise SystemExit('Production release blocked: complete the nationality identity audit first.')
PY
# Test imports and the quota rules before touching the live release.
python3 -m compileall -q "$src/server"
(cd "$src/server" && python3 -m unittest test_import_rules -v)
if ! id riftmanager >/dev/null 2>&1; then
  sudo useradd --system --home-dir "$DATA_ROOT" --shell /usr/sbin/nologin riftmanager
fi
sudo install -d -o root -g root -m 755 "$APP_ROOT"
sudo install -d -o riftmanager -g riftmanager -m 750 "$DATA_ROOT"
sudo install -d -o riftmanager -g riftmanager -m 750 "$DATA_ROOT/backups"
if sudo test -s "$DATA_ROOT/server.db"; then
  backup="$DATA_ROOT/backups/server-$(date -u +%Y%m%dT%H%M%SZ).db"
  sudo sqlite3 "$DATA_ROOT/server.db" ".backup '$backup'"
  sudo chown riftmanager:riftmanager "$backup"
  sudo chmod 600 "$backup"
  echo "Database backed up to $backup"
fi
# Keep code read-only to the service account; mutable SQLite/replays live under DATA_ROOT.
for folder in server engine web assets; do
  sudo install -d -m 755 "$APP_ROOT/$folder"
  sudo rsync -a --delete --exclude='__pycache__/' "$src/$folder/" "$APP_ROOT/$folder/"
done
sudo chown -R root:root "$APP_ROOT"
if [[ ! -x "$APP_ROOT/.venv/bin/python" ]]; then
  sudo python3 -m venv "$APP_ROOT/.venv"
fi
sudo "$APP_ROOT/.venv/bin/python" -m pip install --disable-pip-version-check --upgrade pip pillow
sudo install -m 644 "$src/server/rift-manager.service" /etc/systemd/system/rift-manager.service
sudo install -m 644 "$src/server/rift-match-worker.service" /etc/systemd/system/rift-match-worker.service
sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
$DOMAIN {
    encode zstd gzip
    reverse_proxy 127.0.0.1:8770
    header X-Content-Type-Options nosniff
    header Referrer-Policy strict-origin-when-cross-origin
}
EOF
sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl daemon-reload
sudo systemctl enable --now rift-manager.service
sudo systemctl enable --now rift-match-worker.service
sudo systemctl enable --now caddy.service
sudo systemctl restart rift-manager.service rift-match-worker.service
sudo systemctl reload caddy.service
curl --fail --show-error --silent --retry 5 --retry-delay 1 http://127.0.0.1:8770/health
echo
echo "App services installed. Verify DNS A for $DOMAIN and TLS: curl -I https://$DOMAIN"
echo "Status: sudo systemctl status rift-manager rift-match-worker caddy"
echo "Logs: sudo journalctl -u rift-manager -u rift-match-worker -n 100 --no-pager"
