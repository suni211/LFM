"""Public client update files. Names are fixed so a request cannot leave the update directory."""
import os
import re
from pathlib import Path

ROOT = Path(os.environ.get('RIFT_UPDATES', '/var/lib/rift-manager/updates'))
CHANNELS = {
    'windows': re.compile(r'latest\.json|RiftManagerNative-\d+\.exe'),
    'android': re.compile(r'latest\.json|\d+\.apk'),
}

def serve(handler, path):
    parts = [part for part in path.split('/') if part]
    if len(parts) != 3 or parts[0] != 'updates' or parts[1] not in CHANNELS or not CHANNELS[parts[1]].fullmatch(parts[2]):
        return handler.reply(404, {'error': 'not found'})
    root = ROOT.resolve()
    directory = (root / parts[1]).resolve()
    file = (directory / parts[2]).resolve()
    if file.parent != directory or not file.is_file():
        return handler.reply(404, {'error': 'not found'})
    kind = 'application/json' if file.suffix == '.json' else 'application/vnd.android.package-archive' if file.suffix == '.apk' else 'application/octet-stream'
    handler.send_response(200)
    handler.send_header('Content-Type', kind)
    handler.send_header('Content-Length', str(file.stat().st_size))
    handler.send_header('Cache-Control', 'no-store')
    handler.end_headers()
    with file.open('rb') as source:
        while True:
            chunk = source.read(65536)
            if not chunk:
                break
            handler.wfile.write(chunk)
