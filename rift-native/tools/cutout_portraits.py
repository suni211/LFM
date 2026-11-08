"""Remove portrait backgrounds in place. Safe to rerun: transparent files are skipped."""
import shutil
from pathlib import Path

from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "portraits"
COPIES = [ROOT / "dist" / "assets" / "portraits", ROOT / "build" / "Release" / "assets" / "portraits"]

def already_cut(path):
    with Image.open(path) as image:
        if image.mode != "RGBA":
            return False
        return image.getchannel("A").getextrema()[0] < 250

def main():
    session = new_session("u2net")
    files = sorted(SOURCE.glob("*.png"))
    for index, path in enumerate(files, 1):
        if already_cut(path):
            print(f"skip {index}/{len(files)} {path.name}", flush=True)
            continue
        with Image.open(path) as image:
            result = remove(image.convert("RGBA"), session=session)
        temporary = path.with_suffix(".png.tmp")
        result.save(temporary, "PNG")
        temporary.replace(path)
        for folder in COPIES:
            if folder.is_dir():
                shutil.copy2(path, folder / path.name)
        print(f"cut {index}/{len(files)} {path.name}", flush=True)
    print(f"finished {len(files)}", flush=True)

if __name__ == "__main__":
    main()
