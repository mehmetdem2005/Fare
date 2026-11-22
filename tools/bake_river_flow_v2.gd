extends SceneTree
## Rebuild flow v2 for the extended 7x7 baked corridor (14 river chunks).
func _initialize() -> void:
    call_deferred("_build")
func _build() -> void:
    var profile: RiverProfile=RiverProfile.new()
    var flow: RiverFlowField=RiverFlowField.new()
    var folder: String=RiverFlowAtlasCache.PACK_FOLDER
    if DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(folder))!=OK:
        push_error("RIVER_FLOW_V2_BAKE_FAIL folder")
        quit(2)
        return
    var count: int=0
    for z in range(-3,4):
        for x in [-1,0]:
            var co: Vector2i=Vector2i(x,z)
            var img: Image=flow.build_atlas(profile,Vector2(float(x)*40.0,float(z)*40.0),40.0,32)
            var path: String=folder+"flow_%d_%d.res" % [x,z]
            if ResourceSaver.save(img,path)!=OK:
                push_error("RIVER_FLOW_V2_BAKE_FAIL "+path)
                quit(2)
                return
            count+=1
    print("RIVER_FLOW_V2_BAKE_OK resources=",count," flow=vortex_pockets")
    quit(0)
