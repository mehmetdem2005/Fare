#!/usr/bin/env python3
"""Official Poly Haven CC0 maps. Keep sRGB albedo separate from LINEAR normal/rough.
Packs OpenGL normal RGB + roughness A into one mobile-suitable PNG.
Idempotent output and provenance manifest; failed/missing maps are fatal.
"""
import hashlib
import io
import json
import time
import urllib.request
from pathlib import Path
from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "assets" / "ground"
ASSETS = {
    "grass": "grass_ground",
    "forest": "grass_path_2",
    "rock": "rocks_ground_09",
    "pebbles": "river_small_rocks",
}
HEADERS = {"User-Agent": "FareVadisiGodotMobile/2.0 (Poly Haven CC0; github.com/mehmetdem2005/Fare)"}
KEYS = {"diffuse": ("Diffuse", "diffuse"), "normal": ("nor_gl", "Normal"), "roughness": ("Rough", "rough", "Roughness")}

def download(url):
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=50) as response:
                return response.read()
        except Exception as exc:
            last = exc
            time.sleep(attempt + 1)
    raise RuntimeError("Poly Haven download failed: %s (%s)" % (url, last))

def item_for(info, kind):
    record = None
    for key in KEYS[kind]:
        if key in info:
            record = info[key]
            break
    if not isinstance(record, dict):
        raise ValueError("Missing real %s map; keys=%s" % (kind, list(info)))
    for size in ("1k", "2k"):
        options = record.get(size, {})
        # Prefer PNG for OpenGL normals to preserve XY precision.
        formats = ("png", "jpg", "webp") if kind == "normal" else ("jpg", "png", "webp")
        for fmt in formats:
            item = options.get(fmt)
            if isinstance(item, dict) and item.get("url"):
                return item
    raise ValueError("No usable real %s map; resolutions=%s" % (kind,list(record)))

def resized(blob, mode):
    im = Image.open(io.BytesIO(blob)).convert(mode)
    if im.size != (1024, 1024):
        im = im.resize((1024,1024),Image.Resampling.LANCZOS)
    return im

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest = {"schema": 2, "source": "Poly Haven", "license": "CC0", "normal_convention": "OpenGL +Y", "packed_format": "normal_RBG_roughness_A_unorm_linear", "materials": {}}
    for name, slug in ASSETS.items():
        records = json.loads(download("https://api.polyhaven.com/files/" + slug))
        kinds = {kind:item_for(records,kind) for kind in KEYS}
        file_color = OUT / (name+".jpg")
        file_pack = OUT / (name+"_nrough.png")
        # Avoid decoding/redownloading 12 maps every CI run when already bundled.
        # Provenance is rederived through the *official* API, never invented.
        cached = file_color.is_file() and file_pack.is_file()
        if not cached:
            diffuse = resized(download(kinds["diffuse"]["url"]), "RGB")
            normal = resized(download(kinds["normal"]["url"]), "RGB")
            rough = resized(download(kinds["roughness"]["url"]), "L")
            diffuse.save(file_color,"JPEG",quality=88,optimize=True,subsampling=0)
            rr,gg,bb = normal.split()
            Image.merge("RGBA",(rr,gg,bb,rough)).save(file_pack,"PNG",optimize=True)
        with Image.open(file_pack) as img:
            if img.size != (1024,1024) or img.mode != "RGBA":
                raise ValueError("Packed image invalid: "+str(file_pack))
        manifest["materials"][name] = {
            "asset":slug,
            "asset_page":"https://polyhaven.com/a/"+slug,
            "sources":{kind:entry["url"] for kind,entry in kinds.items()},
            "outputs":{"albedo":file_color.name,"normal_rough":file_pack.name},
            "sha256":{file_color.name:hashlib.sha256(file_color.read_bytes()).hexdigest(),file_pack.name:hashlib.sha256(file_pack.read_bytes()).hexdigest()}
        }
        print("PBR_OK",name,slug,file_pack.stat().st_size,"bytes",flush=True)
    (OUT / "polyhaven_sources.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("POLY_HAVEN_ALL_OK",flush=True)

if __name__ == "__main__":
    main()
