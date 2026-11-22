#!/usr/bin/env python3
"""Download REAL Poly Haven CC0 textures to the repository (not procedural stand-ins)."""
import io, json, sys, time, urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "ground"
ASSETS = {
    "grass": "grass_ground",
    "forest": "grass_path_2",
    "rock": "rocks_ground_09",
    "pebbles": "river_small_rocks",
}
HEADERS = {"User-Agent": "FareVadisiGame/1.0 (PolyHavenCC0Importer; github.com/mehmetdem2005/Fare)"}

def download(url: str) -> bytes:
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=50) as res:
                return res.read()
        except Exception as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Could not download {url}: {last}")

def diffuse(info):
    for key in ("Diffuse", "diffuse", "Base Color", "basecolor"):
        if key in info:
            return info[key]
    raise KeyError(f"Poly Haven diffuse file missing, available maps: {list(info)}")

def fetch_one(label, slug):
    info = json.loads(download(f"https://api.polyhaven.com/files/{slug}"))
    records = diffuse(info)
    for resolution in ("1k", "2k", "4k"):
        options = records.get(resolution, {})
        for fmt in ("jpg", "png", "webp"):
            item = options.get(fmt)
            if isinstance(item, dict) and item.get("url"):
                image_bytes = download(item["url"])
                img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                if img.size != (1024, 1024):
                    img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
                dst = OUT / f"{label}.jpg"
                img.save(dst, format="JPEG", quality=88, optimize=True, subsampling=0)
                print(f"POLY_HAVEN_OK {slug} {item['url']} -> {dst} {dst.stat().st_size} bytes", flush=True)
                return
    raise ValueError(f"Missing diffuse JPEG/PNG for {slug}")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, slug in ASSETS.items():
        fetch_one(name, slug)
    print("POLY_HAVEN_ALL_OK", flush=True)

if __name__ == "__main__":
    main()
