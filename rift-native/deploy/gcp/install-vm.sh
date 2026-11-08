#!/usr/bin/env bash
# Run on an EXISTING Ubuntu GCP VM (no VM or repo is created).
# REF=main bash install-vm.sh  # run as a sudo-capable SSH user
set -euo pipefail
REF="${REF:-main}"
DOMAIN="${DOMAIN:-lol.lcktcg.com}"
APP_ROOT="/opt/lfm"
DATA_ROOT="/var/lib/lfm"
REPO="https://github.com/suni211/LFM.git"
REQUIRE_VERIFIED="${REQUIRE_VERIFIED:-0}"
if [[ "$EUID" -eq 0 ]]; then
  echo 'Run as the ordinary SSH user with sudo access, not as root.' >&2
  exit 1
fi
if [[ ! "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]]; then echo "Invalid domain" >&2; exit 1; fi
command -v sudo >/dev/null || { echo 'sudo is required' >&2; exit 1; }
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl git rsync sqlite3 python3 python3-venv python3-pip
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git clone --depth=1 --filter=blob:none --sparse --branch="$REF" "$REPO" "$tmp/repo"
git -C "$tmp/repo" sparse-checkout set \
  rift-native/server rift-native/engine rift-native/web rift-native/assets rift-native/deploy/gcp
src="$tmp/repo/rift-native"
# A missing game country is visibly pending, not disguised as verified citizenship.
# Optional REQUIRE_VERIFIED=1 blocks release until every real identity is verified.
python3 - "$src/assets/people.json" "$src/assets/nationality-overrides.json" "$REQUIRE_VERIFIED" <<'PY'
import json,sys
people=json.load(open(sys.argv[1],encoding='utf8'))['people']
known=json.load(open(sys.argv[2],encoding='utf8')).get('people',{})
missing=[p for p in people if p.get('real_person') and
         not (p.get('nationality_code') or (known.get(p['id']) or {}).get('code'))]
print('Total people:',len(people),'Real people without game country:',len(missing))
if missing and sys.argv[3]=='1':
    raise SystemExit('Strict release blocked: missing sourced countries.')
PY
# Test imports and the quota rules before touching the live release.
python3 -m compileall -q "$src/server"
(cd "$src/server" && python3 -m unittest test_season_structure test_season_calendar test_player_economy test_renewal_access test_fan_variety test_lineup_readiness -v)
if ! id lfm >/dev/null 2>&1; then
  sudo useradd --system --home-dir "$DATA_ROOT" --shell /usr/sbin/nologin lfm
fi
sudo install -d -o root -g root -m 755 "$APP_ROOT"
sudo install -d -o lfm -g lfm -m 750 "$DATA_ROOT"
sudo install -d -o lfm -g lfm -m 750 "$DATA_ROOT/backups"
# Quiesce only LFM services before snapshot and file updates.
# Other services (including existing lol-card-game) remain untouched.
sudo systemctl stop lfm-match-worker.service 2>/dev/null || true
sudo systemctl stop lfm-api.service 2>/dev/null || true
if sudo test -s "$DATA_ROOT/server.db"; then
  backup="$DATA_ROOT/backups/server-$(date -u +%Y%m%dT%H%M%SZ).db"
  sudo sqlite3 "$DATA_ROOT/server.db" ".backup '$backup'"
  sudo chown lfm:lfm "$backup"
  sudo chmod 600 "$backup"
  echo "Database backed up to $backup"
fi
# Keep code read-only to the service account; mutable SQLite/replays live under DATA_ROOT.
for folder in server engine web assets; do
  sudo install -d -m 755 "$APP_ROOT/$folder"
  sudo rsync -a --delete --exclude='__pycache__/' "$src/$folder/" "$APP_ROOT/$folder/"
done
sudo chown -R root:root "$APP_ROOT"
# A failed redeploy leaves the saved SQLite backup under /var/lib/lfm/backups.
# Inspect health logs before retrying; do not delete or blindly restore data.
if [[ ! -x "$APP_ROOT/.venv/bin/python" ]]; then
  sudo python3 -m venv "$APP_ROOT/.venv"
fi
sudo "$APP_ROOT/.venv/bin/python" -m pip install --disable-pip-version-check --upgrade pip pillow
sudo install -m 644 "$src/deploy/gcp/lfm-api.service" /etc/systemd/system/lfm-api.service
sudo install -m 644 "$src/deploy/gcp/lfm-match-worker.service" /etc/systemd/system/lfm-match-worker.service
# DO NOT overwrite an existing Caddy/Nginx config or expose the API publicly.
# Configure the existing proxy's domain separately (see README).
sudo systemctl daemon-reload
sudo systemctl enable --now lfm-api.service
sudo systemctl enable --now lfm-match-worker.service
sudo systemctl restart lfm-api.service lfm-match-worker.service
curl --fail --show-error --silent --retry 5 --retry-delay 1 http://127.0.0.1:8871/health
echo
echo "LFM installed on existing VM. Point only your LFM reverse-proxy site to 127.0.0.1:8871."
echo "Status: sudo systemctl status lfm-api lfm-match-worker"
echo "Logs: sudo journalctl -u lfm-api -u lfm-match-worker -n 100 --no-pager"
