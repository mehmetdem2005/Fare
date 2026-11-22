#!/usr/bin/env python3
"""Give each CI diagnostics APK a distinct Android identity and visible source SHA."""
from pathlib import Path
import re
import sys

sha = sys.argv[1].strip().lower() if len(sys.argv) > 1 else ""
if not re.fullmatch(r"[0-9a-f]{40}", sha):
    raise SystemExit("Need exact 40-hex Git commit SHA")
short = sha[:8]
identity = Path("scripts/s9_build_identity.gd")
identity.write_text(
    "class_name S9BuildIdentity\n"
    "extends RefCounted\n"
    "# Built by CI from source commit: " + sha + "\n"
    'const BUILD_SHA: String = "' + sha + '"\n'
    'const BUILD_TAG: String = "S9-' + short + '"\n',
    encoding="utf-8",
)
preset = Path("export_presets.cfg")
data = preset.read_text(encoding="utf-8")
def change(pattern, replacement):
    global data
    data, found = re.subn(pattern, replacement, data, count=1)
    if found != 1:
        raise SystemExit("Missing unique export identity field: " + pattern)
change(r'package/unique_name="[^"]+"', 'package/unique_name="org.farevadisi.s9b' + short + '"')
change(r'package/name="[^"]+"', 'package/name="Fare Vadisi S9 ' + short + '"')
change(r'version/name="[^"]+"', 'version/name="0.9.' + short + '"')
preset.write_text(data, encoding="utf-8")
print("S9_BUILD_ID_OK", sha, "org.farevadisi.s9b" + short)
