#!/usr/bin/env python3
"""Fail CI if packed Poly Haven textures are placeholders, corrupt, or mismatched."""
import hashlib
import json
from pathlib import Path
from PIL import Image,ImageStat

OUT=Path(__file__).resolve().parents[1]/"assets"/"ground"
manifest=json.loads((OUT/"polyhaven_sources.json").read_text())
assert manifest["license"]=="CC0"
assert manifest["normal_convention"]=="OpenGL +Y"
assert len(manifest["materials"])==4
for label,material in manifest["materials"].items():
    assert len(material["sources"])==3 and all(u.startswith("https://dl.polyhaven.org/") for u in material["sources"].values())
    for filename,checksum in material["sha256"].items():
        file=OUT/filename
        assert file.is_file(),file
        assert hashlib.sha256(file.read_bytes()).hexdigest()==checksum,file
    with Image.open(OUT/(label+".jpg")) as albedo,Image.open(OUT/(label+"_nrough.png")) as nr:
        assert albedo.size==nr.size==(1024,1024)
        assert nr.mode=="RGBA"
        stats=ImageStat.Stat(nr)
        assert stats.stddev[0]>1.0 and stats.stddev[1]>1.0 and stats.stddev[2]>1.0, label+" is flat normal"
        assert stats.stddev[3]>0.5, label+" is flat roughness"
    print("PBR_IMAGE_VALIDATED",label)
print("PBR_MANIFEST_OK")
