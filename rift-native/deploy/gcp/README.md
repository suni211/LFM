# LFM: GCP Compute Engine + SSH + transfer market

This is **deployment preparation**, not evidence of an existing VM. A billing-enabled Google Cloud project and IAM permissions are required before any GCP resources can be created.

## 1. Google Cloud Shell commands

Open <https://console.cloud.google.com/?cloudshell=true>.

```bash
export PROJECT_ID="YOUR_GCP_PROJECT_ID"   # change to real project ID
export ZONE="asia-northeast3-a"             # Seoul
gcloud config set project "$PROJECT_ID"

curl -fsSLo provision-gcp.sh \
  https://raw.githubusercontent.com/suni211/LFM/fix/nationality-audit-2026-11-08/rift-native/deploy/gcp/provision-gcp.sh
less provision-gcp.sh
PROJECT_ID="$PROJECT_ID" bash provision-gcp.sh
```

The provisioner creates a Seoul e2-medium instance with 4 GiB RAM and 30 GB pd-balanced, a regional static external IP, a dedicated VPC, inbound HTTP/HTTPS and IAP-only SSH. Charges apply for VM hours, disk, external IPv4 and egress.

Set the DNS **A** record for `lol.lcktcg.com` to the public IP returned by the provisioner. The script does not control your DNS provider. Configure GCP budget alerts and grant the invoking account appropriate Compute Engine/IAP TCP tunneling/OS Login IAM permissions.

## 2. Connect to new VM via SSH

```bash
gcloud compute ssh lfm-web-01 \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --tunnel-through-iap
```

No default SSH password or hardcoded private key is created.

## 3. Install on the VM (after merging the reviewed PR)

```bash
curl -fsSLo install-vm.sh \
  https://raw.githubusercontent.com/suni211/LFM/main/rift-native/deploy/gcp/install-vm.sh
less install-vm.sh
REF=main REQUIRE_VERIFIED=1 bash install-vm.sh
```

The installer deliberately **blocks public deployment while any real player's/coach's/staff's nationality_code is missing**. Current initial snapshot: 1,088 persons, only five with a nationality code. The [audit instructions](../../NATIONALITY_AUDIT.md) describe the verification queue. Do not bypass the verification gate for public release.

App URLs once deployed:

- `https://lol.lcktcg.com/`
- `https://lol.lcktcg.com/health`

Services: Python API on localhost TCP 8770, one match worker, Caddy HTTPS. SQLite DB persists at `/var/lib/rift-manager/server.db`, outside the code directory. Existing DB is backed up before deployments.

## 4. SSH health and monitoring commands

```bash
sudo systemctl status rift-manager rift-match-worker caddy --no-pager
sudo journalctl -u rift-manager -u rift-match-worker -n 100 --no-pager
curl -fsS http://127.0.0.1:8770/health
curl -fsS https://lol.lcktcg.com/health
sudo du -sh /var/lib/rift-manager
free -h
df -h
```

## 5. New transfer news behavior

- **Rumors**: `GET /transfer-rumors?id=CAREER_ID&league=LCK` contains rumor-only information, including AI contacts.
- **Official**: `GET /transfer-activity?id=CAREER_ID&league=LCK` contains only completed human or AI transfers and persists player identity, old/new team, fee, season, week and league.
- **Own offers**: `GET /transfer-offers?id=CAREER_ID` retains approval/decline/cancel workflow.
- AI-to-AI completed signings occur in eligible stove weeks when moving a spare-position player between unmanaged clubs, and persist in SQLite. They affect team profiles and future AI rumor sources. Claimed/user-managed clubs are excluded.
- These are in-game AI simulations, not real-world esports transactions. Simulated fees must not be misrepresented as verified real-world transfer payments.

## 6. Current rollout gate

The GitHub work is on `fix/nationality-audit-2026-11-08` / draft PR #1. Do not assume `main` contains it until the PR is reviewed and merged. The server has not been provisioned and DNS has not been changed through this workflow.
