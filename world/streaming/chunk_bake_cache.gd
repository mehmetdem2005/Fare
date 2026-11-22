class_name ChunkBakeCache
extends RefCounted
## S8-A versioned disk-cache for deterministic 40m chunks.
## The gameplay scenes are NEVER serialized, only Mesh, Shape and Image.
const PACK_ROOT: String = "res://assets/baked_chunks/v3/"
const USER_ROOT: String = "user://world_cache/v3/"
const MAX_USER_CHUNKS: int = 100
static var bypass_disk: bool = false
var hits: int = 0
var misses: int = 0
var saved_user: int = 0

func _prefix(co: Vector2i, pack: bool) -> String:
    return (PACK_ROOT if pack else USER_ROOT) + "c_%d_%d_" % [co.x,co.y]

func _from(co: Vector2i, pack: bool) -> Dictionary:
    var p: String = _prefix(co,pack)
    if not FileAccess.file_exists(p+"terrain.res") or not FileAccess.file_exists(p+"collision.res"):
        return {}
    var terrain: ArrayMesh = ResourceLoader.load(p+"terrain.res") as ArrayMesh
    var collider: ConcavePolygonShape3D = ResourceLoader.load(p+"collision.res") as ConcavePolygonShape3D
    if terrain == null or collider == null:
        return {}
    var output: Dictionary = {"terrain":terrain,"collision":collider,"source":"pack" if pack else "user"}
    if FileAccess.file_exists(p+"water.res") and FileAccess.file_exists(p+"flow.res"):
        var water: ArrayMesh = ResourceLoader.load(p+"water.res") as ArrayMesh
        var flow: Image = ResourceLoader.load(p+"flow.res") as Image
        if water != null and flow != null:
            output["water"]=water
            output["flow"]=flow
    return output

func load_chunk(co: Vector2i) -> Dictionary:
    if bypass_disk:
        misses+=1
        return {}
    var chunk: Dictionary = _from(co,true)
    if chunk.is_empty():
        chunk=_from(co,false)
    if chunk.is_empty():
        misses+=1
    else:
        hits+=1
    return chunk

func has_user(co: Vector2i) -> bool:
    var p: String=_prefix(co,false)
    return FileAccess.file_exists(p+"terrain.res") and FileAccess.file_exists(p+"collision.res")

func has_pack(co: Vector2i) -> bool:
    var p: String = _prefix(co,true)
    return FileAccess.file_exists(p+"terrain.res") and FileAccess.file_exists(p+"collision.res")

func save_chunk(co: Vector2i, node: Node3D, packed: bool) -> bool:
    var dir: String = PACK_ROOT if packed else USER_ROOT
    var prefix: String = _prefix(co,packed)
    if DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir)) != OK:
        return false
    var terrain: MeshInstance3D = node.get_node_or_null("Terrain") as MeshInstance3D
    var collider: CollisionShape3D = node.get_node_or_null("TerrainCollider/TerrainCollisionShape") as CollisionShape3D
    if terrain == null or collider == null or terrain.mesh == null or collider.shape == null:
        return false
    if ResourceSaver.save(terrain.mesh,prefix+"terrain.res") != OK:
        return false
    if ResourceSaver.save(collider.shape,prefix+"collision.res") != OK:
        return false
    var water: MeshInstance3D = node.get_node_or_null("FlowingWater") as MeshInstance3D
    if water != null and water.has_meta("flow_image"):
        var flow: Image = water.get_meta("flow_image") as Image
        if flow == null or water.mesh == null:
            return false
        if ResourceSaver.save(water.mesh,prefix+"water.res") != OK:
            return false
        if ResourceSaver.save(flow,prefix+"flow.res") != OK:
            return false
    if not packed:
        saved_user+=1
        if saved_user % 8 == 0:
            prune_user_disk()
    return true

func prune_user_disk() -> void:
    var absolute: String = ProjectSettings.globalize_path(USER_ROOT)
    if not DirAccess.dir_exists_absolute(absolute):
        return
    var names: Array[String] = []
    for name in DirAccess.get_files_at(USER_ROOT):
        if name.ends_with("_terrain.res"):
            names.append(name.trim_suffix("terrain.res"))
    if names.size() <= MAX_USER_CHUNKS:
        return
    names.sort_custom(func(a: String,b: String) -> bool:
        return FileAccess.get_modified_time(USER_ROOT+a+"terrain.res") < FileAccess.get_modified_time(USER_ROOT+b+"terrain.res"))
    for i in range(names.size()-MAX_USER_CHUNKS):
        for suffix in ["terrain.res","collision.res","water.res","flow.res"]:
            var file: String = USER_ROOT+names[i]+suffix
            if FileAccess.file_exists(file):
                DirAccess.remove_absolute(ProjectSettings.globalize_path(file))
