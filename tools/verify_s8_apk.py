#!/usr/bin/env python3
"""Validate actual Android debug APK, 64-bit payload and ZIP integrity."""
import json
import sys
import zipfile
from pathlib import Path
path=Path(sys.argv[1])
if not path.is_file() or path.stat().st_size<12000000:
    raise SystemExit("ANDROID_APK_FAIL: tiny/missing file")
with zipfile.ZipFile(path) as f:
    broken=f.testzip()
    if broken:
        raise SystemExit("ANDROID_APK_FAIL: corrupted ZIP entry "+broken)
    names=f.namelist()
    libraries=[n for n in names if n.startswith("lib/arm64-v8a/") and n.endswith(".so")]
    if not libraries or "AndroidManifest.xml" not in names:
        raise SystemExit("ANDROID_APK_FAIL: no 64-bit engine or manifest")
    if not any(n.startswith("assets/") for n in names):
        raise SystemExit("ANDROID_APK_FAIL: project payload missing")
    print("ANDROID_APK_PACKAGE_OK",json.dumps({
        "name":path.name,"bytes":path.stat().st_size,"entries":len(names),
        "arm64_libraries":libraries,"manifest":"AndroidManifest.xml",
        "project_payload":True,"debug_only":True,"device_tested":False
    },sort_keys=True))
