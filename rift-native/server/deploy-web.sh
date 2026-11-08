sudo install -d -m 755 /srv/rift-manager
sudo install -m 644 /tmp/index.html /tmp/client.js /srv/rift-manager/
sudo python3 - <<'PY'
from pathlib import Path
p=Path('/etc/caddy/Caddyfile')
original=p.read_text()
if 'handle_path /rift/api/*' not in original:
    marker='berrple.com {\n'
    assert original.startswith(marker)
    Path('/etc/caddy/Caddyfile.pre-rift').write_text(original)
    p.write_text(original.replace(marker,marker+''' redir /rift /rift/ 308
 handle_path /rift/api/* {
  reverse_proxy 127.0.0.1:8770
 }
 handle_path /rift/* {
  root * /srv/rift-manager
  header X-Content-Type-Options nosniff
  file_server
 }
''',1))
PY
if sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy; then
 curl -fsS https://berrple.com/rift/api/health
else
 sudo cp /etc/caddy/Caddyfile.pre-rift /etc/caddy/Caddyfile
 exit 1
fi
