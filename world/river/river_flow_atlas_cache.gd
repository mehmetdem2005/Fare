class_name RiverFlowAtlasCache
extends RefCounted
## Separate flow schema version. Terrain meshes and collision resource packs
## remain at S8-A v3; S3 vortex changes MUST invalidate only the flow atlas.
const PACK_FOLDER: String = "res://assets/river_flow_v2/"
const USER_FOLDER: String = "user://river_flow_v2/"
const RESOLUTION: int = 32
const MAX_USER_FILES: int = 100
var loaded_packed: int = 0
var loaded_user: int = 0
var regenerated: int = 0

func _filename(co: Vector2i, packed: bool) -> String:
    return (PACK_FOLDER if packed else USER_FOLDER) + "flow_%d_%d.res" % [co.x,co.y]

func _load_image(path: String) -> Image:
    if not FileAccess.file_exists(path):
        return null
    var image: Image = ResourceLoader.load(path) as Image
    if image == null or image.get_width()!=RESOLUTION or image.get_height()!=RESOLUTION or image.get_format()!=Image.FORMAT_RGBA8:
        return null
    return image

func fetch(co: Vector2i, profile: RiverProfile, field: RiverFlowField, cell: float) -> Image:
    var pack: Image=_load_image(_filename(co,true))
    if pack!=null:
        loaded_packed+=1
        return pack
    var user: Image=_load_image(_filename(co,false))
    if user!=null:
        loaded_user+=1
        return user
    var origin: Vector2=Vector2(float(co.x)*cell,float(co.y)*cell)
    var generated: Image=field.build_atlas(profile,origin,cell,RESOLUTION)
    regenerated+=1
    var folder: String=ProjectSettings.globalize_path(USER_FOLDER)
    if DirAccess.make_dir_recursive_absolute(folder)==OK:
        ResourceSaver.save(generated,_filename(co,false))
        if regenerated%8==0:
            _prune_user()
    return generated

func _prune_user() -> void:
    if not DirAccess.dir_exists_absolute(ProjectSettings.globalize_path(USER_FOLDER)):
        return
    var names: Array[String]=[]
    for name in DirAccess.get_files_at(USER_FOLDER):
        if name.begins_with("flow_") and name.ends_with(".res"):
            names.append(name)
    if names.size()<=MAX_USER_FILES:
        return
    names.sort_custom(func(a: String,b: String) -> bool:
        return FileAccess.get_modified_time(USER_FOLDER+a)<FileAccess.get_modified_time(USER_FOLDER+b))
    for i in range(names.size()-MAX_USER_FILES):
        DirAccess.remove_absolute(ProjectSettings.globalize_path(USER_FOLDER+names[i]))
