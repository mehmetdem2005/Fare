extends SceneTree
func _initialize() -> void:
    call_deferred("_run")
func _fail(reason: String) -> void:
    push_error("S3_FLOW_V2_FAIL "+reason)
    quit(2)
func _run() -> void:
    var profile: RiverProfile=RiverProfile.new()
    var field: RiverFlowField=RiverFlowField.new()
    var cache: RiverFlowAtlasCache=RiverFlowAtlasCache.new()
    var checked: int=0
    for z in range(-3,13):
        for x in [-1,0]:
            var co: Vector2i=Vector2i(x,z)
            var img: Image=cache.fetch(co,profile,field,40.0)
            if img==null or img.get_width()!=32 or img.get_height()!=32:
                _fail("v2 cached flow atlas missing at "+str(co))
                return
            var pixel: Vector2i=Vector2i(14,14)
            var pos: Vector2=Vector2(float(x)*40.0,float(z)*40.0)+Vector2(float(pixel.x),float(pixel.y))*40.0/31.0
            var actual: Vector2=field.sample(profile,pos)["velocity"]
            var packed: Vector2=field.decode_rg(img.get_pixel(pixel.x,pixel.y))
            if actual.distance_to(packed)>0.045:
                _fail("cached GPU v2 vector differs from real physics "+str(co))
                return
            checked+=1
    if cache.loaded_packed!=32 or cache.regenerated>0:
        _fail("32 assets not actually precompiled; packed="+str(cache.loaded_packed)+" rebuilt="+str(cache.regenerated))
        return
    var scene: PackedScene=load("res://scenes/main.tscn") as PackedScene
    var game: Node3D=scene.instantiate() as Node3D
    root.add_child(game)
    var water: MeshInstance3D=game.get_node("Chunk_0_0/FlowingWater") as MeshInstance3D
    var flowing: Image=water.get_meta("flow_image") as Image
    var packed_image: Image=cache.fetch(Vector2i(0,0),profile,field,40.0)
    if flowing.get_data()!=packed_image.get_data():
        _fail("live shader image is stale v3, not new v2")
        return
    print("S3_FLOW_V2_OK pack_count=",checked," stale_v3_disabled=true shader_cpu_match=true")
    quit(0)
