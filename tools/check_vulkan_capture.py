#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageStat
source=Path("/tmp/s4_mobile_vulkan.png")
assert source.is_file() and source.stat().st_size>10000,"No meaningful rendered PNG"
img=Image.open(source).convert("RGB")
assert img.width>=400 and img.height>=250,(img.width,img.height)
stat=ImageStat.Stat(img)
if max(stat.stddev)<7.0:
    raise AssertionError("Flat-color render, likely missing terrain/water: "+str(stat.stddev))
print("S4_VULKAN_PNG_OK",img.size,"RGB stddev",stat.stddev,"mean",stat.mean)
