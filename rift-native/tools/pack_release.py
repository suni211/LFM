"""Append stored assets to one release executable."""
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "release" / "stage" / "RiftManagerNative.exe"
TARGET = ROOT / "release" / "RiftManager.exe"
MAGIC = 0x31474B5054464952

def main():
    TARGET.parent.mkdir(exist_ok=True)
    payload = ROOT / "release" / "assets.zip"
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in (ROOT / "assets").rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(ROOT).as_posix())
    blob = payload.read_bytes()
    TARGET.write_bytes(SOURCE.read_bytes() + blob + struct.pack("<QQ", len(blob), MAGIC))
    payload.unlink()
    print(TARGET, TARGET.stat().st_size)

if __name__ == "__main__":
    main()
