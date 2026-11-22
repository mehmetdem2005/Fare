class_name S9BuildIdentity
extends RefCounted
## GitHub CI overwrites these literals for every Android diagnostics APK.
## Local editor fallback is deliberately distinguishable from a tested APK.
const BUILD_SHA: String = "local-unstamped"
const BUILD_TAG: String = "S9-LOCAL"
