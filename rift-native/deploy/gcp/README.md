# 기존 GCP VM에 LFM 배포 (저장소/VM 재생성 없음)

대상 GitHub 저장소: https://github.com/suni211/LFM
배포 기준 브랜치: `main`

이 문서는 **이미 생성한 Google Cloud 프로젝트와 Compute Engine VM**을 사용합니다. VM 생성 스크립트를 실행하지 마세요. 서버에 기존 게임이 있는 경우에도 LFM은 독립 서비스로 설치됩니다.

## 1. 기존 인스턴스 확인 및 SSH

Google Cloud Shell이나 gcloud CLI:

```bash
export PROJECT_ID="실제_GCP_프로젝트_ID"
gcloud compute instances list --project "$PROJECT_ID"
gcloud compute ssh "실제_VM_이름" --project "$PROJECT_ID" --zone "실제_ZONE"
```

인스턴스가 외부 IP 없이 IAP를 사용한다면, 적절한 IAM 권한을 확인한 후 `--tunnel-through-iap` 옵션을 사용하세요. 정확한 인스턴스 이름과 zone은 목록에서 확인하세요.

## 2. VM 내에서 패치 배포

```bash
curl -fsSLo install-vm.sh \
  https://raw.githubusercontent.com/suni211/LFM/main/rift-native/deploy/gcp/install-vm.sh
bash -n install-vm.sh
less install-vm.sh
REF=main bash install-vm.sh
```

설치 스크립트 동작:
- 기존 `suni211/LFM`에서 지정된 ref를 받아 코드만 업데이트합니다.
- 기존 VM 또는 저장소를 새로 생성하지 않습니다.
- 앱: `/opt/lfm`, SQLite 데이터: `/var/lib/lfm/server.db`.
- 기존 `/home/hisam/lol-card-game` 등 별도 서비스에는 접근하지 않습니다.
- 두 LFM 서비스만 멈춘 뒤, 기존 DB가 있으면 `/var/lib/lfm/backups/`로 백업합니다.
- 로컬 포트 `127.0.0.1:8871`에 Python 게임 API를 실행합니다.
- 서비스는 `lfm-api`와 `lfm-match-worker`입니다.
- Caddy/Nginx 설정을 덮어쓰지 않습니다.

국적 검증 중인 선수는 "미확인"으로 표시해야 합니다. `REQUIRE_VERIFIED=1 REF=main bash install-vm.sh`로 실행하면 실제 선수의 국가 코드가 하나라도 누락된 동안 배포를 차단합니다. 일반 실행은 미확인 상태를 유지한 채 설치합니다. 이는 실제 시민권이 모두 확인됐다는 뜻이 아닙니다.

## 3. 기존 HTTPS 프록시에 LFM 도메인만 연결

DNS A 레코드를 해당 GCP VM 공인 IP에 연결합니다. 예시 호스트 `lol.lcktcg.com`은 기존 프로젝트 설정에서 사용된 값이며, 실제 DNS 보유 여부는 확인해야 합니다. 다른 게임용 도메인/라우팅은 유지하세요.

이미 Caddy를 운영한다면 **기존 설정을 덮어쓰지 말고** 해당 호스트 블록만 추가합니다.

```caddy
lol.lcktcg.com {
    encode gzip zstd
    reverse_proxy 127.0.0.1:8871
    header X-Content-Type-Options nosniff
}
```

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Nginx가 실행 중이라면 Caddy를 추가 설치하지 마세요. 현재 Nginx 사이트에 별도 `server_name lol.lcktcg.com`과 `proxy_pass http://127.0.0.1:8871;`를 설정하고 기존 TLS 인증서를 사용하거나 신규 발급해야 합니다.

GCP VPC 방화벽에서 이 VM에 80/443을 허용해야 HTTPS 연결이 됩니다. **8871 포트는 공개하지 마세요.** SSH는 IAP 또는 제한된 소스 IP를 권장합니다.

## 4. 동작 확인

```bash
sudo systemctl status lfm-api lfm-match-worker --no-pager
curl -fsS http://127.0.0.1:8871/health
sudo journalctl -u lfm-api -u lfm-match-worker -n 100 --no-pager
curl -fsS https://lol.lcktcg.com/health
```

외부 HTTPS 검사 명령은 도메인 DNS 및 인증서 설정 후에만 동작합니다.

## 5. 업데이트와 사고 복구

```bash
REF=main bash install-vm.sh
ls -lh /var/lib/lfm/backups/
```

복구가 필요하면 API와 워커 서비스를 먼저 중지하고, 저장한 DB 백업과 해당 시점의 **호환되는 코드 버전**을 함께 복원하세요. 구형 104주 세이브를 150주로 변환한 DB에 구버전 서버 코드만 올리는 것은 안전하지 않습니다.

기존 다른 서비스의 `/etc/caddy/Caddyfile`, nginx 설정, `/home/hisam/lol-card-game` 디렉터리를 삭제하거나 교체하지 마세요.

참고: [Google Cloud SSH 안내](https://cloud.google.com/compute/docs/connect/standard-ssh), [Compute Engine 방화벽](https://cloud.google.com/firewall/docs/using-firewalls)
