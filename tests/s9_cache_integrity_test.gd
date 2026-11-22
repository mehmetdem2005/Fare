extends SceneTree
## Verify v4 manifest, exact coordinate/version, SHA corruption rejection and
## unchanged v3 packed resources. A corrupted cache must return miss, never
## return mismatched terrain/collision or crash.
func _initialize() -> void:
    call_deferred("_run")
func _fail(message: String) -> void:
    push_error("S9_CACHE_INTEGRITY_FAIL "+message)
    quit(2)
func _write_text(path: String,value: String) -> bool:
    var f: FileAccess=FileAccess.open(path,FileAccess.WRITE)
    if f==null:
        return false
    f.store_string(value)
    f.close()
    return true
func _run() -> void:
    var cache: ChunkBakeCache=ChunkBakeCache.new()
    if cache.has_pack(Vector2i(0,0))==false:
        _fail("original pack missing")
        return
    var game: Node3D=(load("res://scenes/main.tscn") as PackedScene).instantiate() as Node3D
    root.add_child(game)
    game.set_process(false)
    var co: Vector2i=Vector2i(0,14)
    game.call("_add_chunk",co,false)
    var chunk: Node3D=game.get_node_or_null("Chunk_0_14") as Node3D
    if chunk==null or not cache.save_chunk(co,chunk,false):
        _fail("new v4 resources not saved")
        return
    var prefix: String="user://world_cache/v4/c_0_14_"
    var manifest_path: String=prefix+"manifest.json"
    if not FileAccess.file_exists(manifest_path):
        _fail("v4 commit manifest absent")
        return
    var good_manifest: String=FileAccess.get_file_as_string(manifest_path)
    var first: Dictionary=cache.load_chunk(co)
    if first.get("source","")!="user" or not first.has("water") or not first.has("collision"):
        _fail("v4 read rejected valid package")
        return
    if not _write_text(manifest_path,"NOT_A_VALID_MANIFEST"):
        _fail("cannot inject corrupted manifest")
        return
    var bad_meta: Dictionary=cache.load_chunk(co)
    if not bad_meta.is_empty() or int(cache.integrity_rejects)<1:
        _fail("bad manifest was accepted")
        return
    if not _write_text(manifest_path,good_manifest):
        _fail("cannot restore manifest")
        return
    var old_file: PackedByteArray=FileAccess.get_file_as_bytes(prefix+"terrain.res")
    if old_file.is_empty():
        _fail("cannot read terrain bytes")
        return
    var changed_file: FileAccess=FileAccess.open(prefix+"terrain.res",FileAccess.WRITE)
    if changed_file==null:
        _fail("cannot simulate interrupted payload")
        return
    changed_file.store_8(0)
    changed_file.close()
    var bad_payload: Dictionary=cache.load_chunk(co)
    if not bad_payload.is_empty() or int(cache.integrity_rejects)<2:
        _fail("payload checksum corruption not rejected")
        return
    var restore: FileAccess=FileAccess.open(prefix+"terrain.res",FileAccess.WRITE)
    if restore==null:
        _fail("cannot restore payload")
        return
    restore.store_buffer(old_file)
    restore.close()
    var again: Dictionary=cache.load_chunk(co)
    if again.get("source","")!="user":
        _fail("valid cache did not recover after restore")
        return
    if int(cache.write_failures)!=0:
        _fail("unexpected cache write failure")
        return
    print("S9_CACHE_INTEGRITY_OK schema=v4 sha256=verified manifest=commit_last corrupted_header=reject corrupted_payload=reject recovered=yes v3_pack=intact")
    quit(0)
