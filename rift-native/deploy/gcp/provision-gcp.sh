#!/usr/bin/env bash
# Run from Google Cloud Shell: PROJECT_ID=my-project bash provision-gcp.sh
# Creates a low-cost Seoul VM, isolated VPC, only HTTP(S) and IAP SSH.
set -euo pipefail
: "${PROJECT_ID:?Set PROJECT_ID to your GCP project ID (billing required)}"
REGION="${REGION:-asia-northeast3}"
ZONE="${ZONE:-asia-northeast3-a}"
NAME="${NAME:-lfm-web-01}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-medium}"
NETWORK="${NETWORK:-lfm-network}"
SUBNET="${SUBNET:-lfm-subnet}"
ADDRESS_NAME="${ADDRESS_NAME:-lfm-public-ip}"
GCLOUD=(gcloud --project="${PROJECT_ID}")
command -v gcloud >/dev/null || { echo 'Install gcloud CLI or use Google Cloud Shell' >&2; exit 1; }

"${GCLOUD[@]}" services enable compute.googleapis.com iap.googleapis.com
if ! "${GCLOUD[@]}" compute networks describe "$NETWORK" >/dev/null 2>&1; then
  "${GCLOUD[@]}" compute networks create "$NETWORK" --subnet-mode=custom
fi
if ! "${GCLOUD[@]}" compute networks subnets describe "$SUBNET" --region="$REGION" >/dev/null 2>&1; then
  "${GCLOUD[@]}" compute networks subnets create "$SUBNET" \
    --region="$REGION" --network="$NETWORK" --range="10.83.0.0/24"
fi
if ! "${GCLOUD[@]}" compute addresses describe "$ADDRESS_NAME" --region="$REGION" >/dev/null 2>&1; then
  "${GCLOUD[@]}" compute addresses create "$ADDRESS_NAME" --region="$REGION" --network-tier=PREMIUM
fi
IP=$("${GCLOUD[@]}" compute addresses describe "$ADDRESS_NAME" --region="$REGION" --format='value(address)')
if ! "${GCLOUD[@]}" compute firewall-rules describe lfm-allow-web >/dev/null 2>&1; then
  "${GCLOUD[@]}" compute firewall-rules create lfm-allow-web \
    --network="$NETWORK" --direction=INGRESS --priority=1000 \
    --source-ranges="0.0.0.0/0" --target-tags="lfm-web" --allow="tcp:80,tcp:443"
fi
if ! "${GCLOUD[@]}" compute firewall-rules describe lfm-allow-iap-ssh >/dev/null 2>&1; then
  "${GCLOUD[@]}" compute firewall-rules create lfm-allow-iap-ssh \
    --network="$NETWORK" --direction=INGRESS --priority=1000 \
    --source-ranges="35.235.240.0/20" --target-tags="lfm-web" --allow="tcp:22"
fi
if "${GCLOUD[@]}" compute instances describe "$NAME" --zone="$ZONE" >/dev/null 2>&1; then
  echo "VM $NAME already exists. Will not overwrite it."
else
  "${GCLOUD[@]}" compute instances create "$NAME" \
    --zone="$ZONE" --machine-type="$MACHINE_TYPE" \
    --subnet="$SUBNET" --address="$IP" --network-tier=PREMIUM \
    --image-family="ubuntu-2404-lts-amd64" --image-project="ubuntu-os-cloud" \
    --boot-disk-size="30GB" --boot-disk-type="pd-balanced" \
    --tags="lfm-web" --no-service-account \
    --metadata="enable-oslogin=TRUE" --labels="app=lfm,role=web"
fi
cat <<EOF

VM: $NAME ($ZONE) - $MACHINE_TYPE
Public IPv4: $IP
DNS: create an A record: lol.lcktcg.com -> $IP
SSH with IAP after granting the required IAP + OS Login roles:
  gcloud compute ssh $NAME --project=$PROJECT_ID --zone=$ZONE --tunnel-through-iap

On the VM, install the app from:
  https://github.com/suni211/LFM/tree/main/rift-native/deploy/gcp

WARNING: VM, persistent disk, external IPv4, and network egress incur charges.
EOF
