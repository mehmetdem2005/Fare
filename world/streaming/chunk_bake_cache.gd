class_name ChunkBakeCache
extends RefCounted
## S9.2 cache integrity: old packaged v3 stays byte-identical.
## New user saves go into v4 with a versioned SHA-256 manifest committed last.
## Legacy v3 app-private cache is readable but never overwritten by new code.
const PACK_ROOT: String="res://assets/baked_chunks/v3/"
const USER_ROOT: String="user://world_cache/v4/"
const LEGACY_USER_ROOT: String="user://world_cache/v3/"
const SCHEMA: int=4
const GENERATOR_VERSION: int=3
const RIVER_VERSION: int=2
const WORLD_SEED: int=88973
const CACHE_MAGIC: String="FVCH"
const MAX_USER_CHUNKS: int=100
static var bypass_disk: bool=false
var hits: int=0
var misses: int=0
var saved_user: int=0
var integrity_rejects: int=0
var legacy_user_hits: int=0
var write_failures: int=0

func _prefix(co: Vector2i,pack: bool) -> String:
    return (PACK_ROOT if pack else USER_ROOT)+"c_%d_%d_" % [co.x,co.y]

func _legacy_prefix(co: Vector2i) -> String:
    return LEGACY_USER_ROOT+"c_%d_%d_" % [co.x,co.y]

func _load_resources(p: String,source: String) -> Dictionary:
    if not FileAccess.file_exists(p+"terrain.res") or not FileAccess.file_exists(p+"collision.res"):
        return {}
    var terrain: ArrayMesh=ResourceLoader.load(p+"terrain.res") as ArrayMesh
    var collider: ConcavePolygonShape3D=ResourceLoader.load(p+"collision.res") as ConcavePolygonShape3D
    if terrain==null or collider==null:
        return {}
    var out: Dictionary={"terrain":terrain,"collision":collider,"source":source}
    if FileAccess.file_exists(p+"water.res") and FileAccess.file_exists(p+"flow.res"):
        var water: ArrayMesh=ResourceLoader.load(p+"water.res") as ArrayMesh
        var flow: Image=ResourceLoader.load(p+"flow.res") as Image
        if water!=null and flow!=null:
            out["water"]=water
            out["flow"]=flow
    return out

func _verify_v4_manifest(co: Vector2i) -> bool:
    var p: String=_prefix(co,false)
    var meta_path: String=p+"manifest.json"
    if not FileAccess.file_exists(meta_path):
        return false
    var meta: Variant=JSON.parse_string(FileAccess.get_file_as_string(meta_path))
    if not meta is Dictionary:
        return false
    if str(meta.get("magic",""))!=CACHE_MAGIC or int(meta.get("schema",-1))!=SCHEMA:
        return false
    if int(meta.get("generator",-1))!=GENERATOR_VERSION or int(meta.get("river",-1))!=RIVER_VERSION:
        return false
    if int(meta.get("world_seed",-1))!=WORLD_SEED:
        return false
    var position: Variant=meta.get("chunk",[])
    if not position is Array or position.size()!=2:
        return false
    if int(position[0])!=co.x or int(position[1])!=co.y:
        return false
    var names: Variant=meta.get("resources",[])
    if not names is Array or names.size()<2 or names.size()>4:
        return false
    var found: Dictionary={}
    for entry_variant in names:
        if not entry_variant is Dictionary:
            return false
        var entry: Dictionary=entry_variant
        var name: String=str(entry.get("name",""))
        if not ["terrain","collision","water","flow"].has(name) or found.has(name):
            return false
        found[name]=true
        var path: String=p+name+".res"
        if not FileAccess.file_exists(path):
            return false
        var file: FileAccess=FileAccess.open(path,FileAccess.READ)
        if file==null or file.get_length()!=int(entry.get("bytes",-1)):
            return false
        file.close()
        if FileAccess.get_sha256(path)!=str(entry.get("sha256","")):
            return false
    return found.has("terrain") and found.has("collision") and (found.has("water")==found.has("flow"))

func _from(co: Vector2i,pack: bool) -> Dictionary:
    if pack:
        return _load_resources(_prefix(co,true),"pack")
    var p: String=_prefix(co,false)
    if FileAccess.file_exists(p+"manifest.json"):
        if not _verify_v4_manifest(co):
            integrity_rejects+=1
            return {}
        return _load_resources(p,"user")
    var legacy: Dictionary=_load_resources(_legacy_prefix(co),"user")
    if not legacy.is_empty():
        legacy_user_hits+=1
    return legacy

func load_chunk(co: Vector2i) -> Dictionary:
    if bypass_disk:
        misses+=1
        return {}
    var chunk: Dictionary=_from(co,true)
    if chunk.is_empty():
        chunk=_from(co,false)
    if chunk.is_empty():
        misses+=1
    else:
        hits+=1
    return chunk

func has_pack(co: Vector2i) -> bool:
    var p: String=_prefix(co,true)
    return FileAccess.file_exists(p+"terrain.res") and FileAccess.file_exists(p+"collision.res")

func has_user(co: Vector2i) -> bool:
    var p: String=_prefix(co,false)
    # This is only a fast scheduling hint. Actual loading verifies the SHA.
    if FileAccess.file_exists(p+"manifest.json"):
        return FileAccess.file_exists(p+"terrain.res") and FileAccess.file_exists(p+"collision.res")
    p=_legacy_prefix(co)
    return FileAccess.file_exists(p+"terrain.res") and FileAccess.file_exists(p+"collision.res")

func _collect_resources(node: Node3D) -> Dictionary:
    var terrain: MeshInstance3D=node.get_node_or_null("Terrain") as MeshInstance3D
    var collider: CollisionShape3D=node.get_node_or_null("TerrainCollider/TerrainCollisionShape") as CollisionShape3D
    if terrain==null or collider==null or terrain.mesh==null or collider.shape==null:
        return {}
    var items: Dictionary={"terrain":terrain.mesh,"collision":collider.shape}
    var water: MeshInstance3D=node.get_node_or_null("FlowingWater") as MeshInstance3D
    if water!=null and water.has_meta("flow_image"):
        var image: Image=water.get_meta("flow_image") as Image
        if image==null or water.mesh==null:
            return {}
        items["water"]=water.mesh
        items["flow"]=image
    return items

func _cleanup_temps(paths: Array[String]) -> void:
    for path in paths:
        if FileAccess.file_exists(path):
            DirAccess.remove_absolute(ProjectSettings.globalize_path(path))

func save_chunk(co: Vector2i,node: Node3D,packed: bool) -> bool:
    var items: Dictionary=_collect_resources(node)
    if items.is_empty():
        return false
    var dir: String=PACK_ROOT if packed else USER_ROOT
    if DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))!=OK:
        write_failures+=1
        return false
    var p: String=_prefix(co,packed)
    if packed:
        # Build-time-only asset baking retains v3 .res layout exactly.
        for name in ["terrain","collision","water","flow"]:
            if items.has(name) and ResourceSaver.save(items[name],p+name+".res")!=OK:
                write_failures+=1
                return false
        return true

    var tmp_paths: Array[String]=[]
    var files: Array[Dictionary]=[]
    for name in ["terrain","collision","water","flow"]:
        if not items.has(name):
            continue
        var tmp: String=p+name+".tmp.res"
        tmp_paths.append(tmp)
        if ResourceSaver.save(items[name],tmp)!=OK:
            write_failures+=1
            _cleanup_temps(tmp_paths)
            return false
        var data: FileAccess=FileAccess.open(tmp,FileAccess.READ)
        if data==null:
            write_failures+=1
            _cleanup_temps(tmp_paths)
            return false
        var byte_size: int=data.get_length()
        data.close()
        files.append({"name":name,"bytes":byte_size,"sha256":FileAccess.get_sha256(tmp)})
    # File rename alone cannot atomically replace all four resources.
    # The SHA-verified manifest is the final commit record.
    for name in ["terrain","collision","water","flow"]:
        if not items.has(name):
            continue
        var temp_file: String=p+name+".tmp.res"
        var destination: String=p+name+".res"
        if DirAccess.rename_absolute(ProjectSettings.globalize_path(temp_file),ProjectSettings.globalize_path(destination))!=OK:
            write_failures+=1
            _cleanup_temps(tmp_paths)
            return false
    var meta: Dictionary={
        "magic":CACHE_MAGIC,"schema":SCHEMA,
        "generator":GENERATOR_VERSION,"river":RIVER_VERSION,"world_seed":WORLD_SEED,
        "chunk":[co.x,co.y],"resources":files
    }
    var temp_meta: String=p+"manifest.tmp"
    var f: FileAccess=FileAccess.open(temp_meta,FileAccess.WRITE)
    if f==null:
        write_failures+=1
        return false
    f.store_string(JSON.stringify(meta))
    f.flush()
    f.close()
    if DirAccess.rename_absolute(ProjectSettings.globalize_path(temp_meta),ProjectSettings.globalize_path(p+"manifest.json"))!=OK:
        write_failures+=1
        return false
    saved_user+=1
    if saved_user%8==0:
        prune_user_disk()
    return true

func prune_user_disk() -> void:
    var absolute: String=ProjectSettings.globalize_path(USER_ROOT)
    if not DirAccess.dir_exists_absolute(absolute):
        return
    var names: Array[String]=[]
    for name in DirAccess.get_files_at(USER_ROOT):
        if name.ends_with("_manifest.json"):
            names.append(name.trim_suffix("manifest.json"))
    if names.size()<=MAX_USER_CHUNKS:
        return
    names.sort_custom(func(a: String,b: String) -> bool:
        return FileAccess.get_modified_time(USER_ROOT+a+"manifest.json")<FileAccess.get_modified_time(USER_ROOT+b+"manifest.json"))
    for i in range(names.size()-MAX_USER_CHUNKS):
        for suffix in ["manifest.json","terrain.res","collision.res","water.res","flow.res"]:
            var path: String=USER_ROOT+names[i]+suffix
            if FileAccess.file_exists(path):
                DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
