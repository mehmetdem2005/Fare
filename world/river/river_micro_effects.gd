class_name RiverMicroEffects
extends Node3D
## S7: 12 flowing leaves, 16 reused wet footprints and 8 droplets/bubbles.
## No allocations per update, no procedural GPU particles or extra render passes.
const LEAF_COUNT: int = 12
const FOOTPRINT_COUNT: int = 16
const DROP_COUNT: int = 8
var profile: RiverProfile
var flow: RiverFlowField
var actor: CharacterBody3D
var mouse_water: MouseWaterInteraction
var height_sampler: Callable
var leaves_mesh: MultiMesh
var drop_mesh: MultiMesh
var leaves: Array[Vector2] = []
var drops: Array[Vector3] = []
var footprints: Array[MeshInstance3D] = []
var footprint_lives: Array[float] = []
var ring_cursor: int = 0
var current_tick: float = 0.0
var print_tick: float = 0.0
var initialized: bool = false
var rng: RandomNumberGenerator = RandomNumberGenerator.new()

func _ready() -> void:
    name="RiverMicroEffects"
    rng.seed=99701
    var leaf_mat: StandardMaterial3D = StandardMaterial3D.new()
    leaf_mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    leaf_mat.vertex_color_use_as_albedo=true
    leaf_mat.cull_mode=BaseMaterial3D.CULL_DISABLED
    var leaf_plane: PlaneMesh = PlaneMesh.new()
    leaf_plane.size=Vector2(0.13,0.07)
    leaf_plane.material=leaf_mat
    leaves_mesh=MultiMesh.new()
    leaves_mesh.transform_format=MultiMesh.TRANSFORM_3D
    leaves_mesh.use_colors=true
    leaves_mesh.mesh=leaf_plane
    leaves_mesh.instance_count=LEAF_COUNT
    var leaves_instance: MultiMeshInstance3D = MultiMeshInstance3D.new()
    leaves_instance.name="FlowLeaves"
    leaves_instance.multimesh=leaves_mesh
    leaves_instance.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    leaves_instance.visibility_range_end=35.0
    add_child(leaves_instance)
    for i in range(LEAF_COUNT):
        leaves.append(Vector2.ZERO)
        leaves_mesh.set_instance_color(i,Color(0.44,0.36,0.16) if i%3==0 else Color(0.27,0.38,0.17))
        leaves_mesh.set_instance_transform(i,Transform3D(Basis.IDENTITY,Vector3(0.0,-100.0,0.0)))
    var footprint_material: StandardMaterial3D=StandardMaterial3D.new()
    footprint_material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    footprint_material.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
    footprint_material.albedo_color=Color(0.11,0.12,0.10,0.27)
    footprint_material.cull_mode=BaseMaterial3D.CULL_DISABLED
    var footprint_plane: PlaneMesh=PlaneMesh.new()
    footprint_plane.size=Vector2(0.13,0.065)
    footprint_plane.material=footprint_material
    for i in range(FOOTPRINT_COUNT):
        var part: MeshInstance3D=MeshInstance3D.new()
        part.name="WetPaw_%d" % i
        part.mesh=footprint_plane
        part.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        part.visible=false
        footprints.append(part)
        footprint_lives.append(0.0)
        add_child(part)
    var drop_mat: StandardMaterial3D=StandardMaterial3D.new()
    drop_mat.albedo_color=Color(0.63,0.82,0.80,0.40)
    drop_mat.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
    drop_mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
    var droplet: SphereMesh=SphereMesh.new()
    droplet.radius=0.014
    droplet.height=0.028
    droplet.radial_segments=6
    droplet.rings=3
    droplet.material=drop_mat
    drop_mesh=MultiMesh.new()
    drop_mesh.transform_format=MultiMesh.TRANSFORM_3D
    drop_mesh.mesh=droplet
    drop_mesh.instance_count=DROP_COUNT
    var drops_instance: MultiMeshInstance3D=MultiMeshInstance3D.new()
    drops_instance.name="WaterDroplets"
    drops_instance.multimesh=drop_mesh
    drops_instance.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    drops_instance.visibility_range_end=18.0
    add_child(drops_instance)
    for i in range(DROP_COUNT):
        drops.append(Vector3(0.0,-100.0,0.0))
        drop_mesh.set_instance_transform(i,Transform3D(Basis.IDENTITY,drops[i]))
    initialized=true

func _respawn_leaf(i: int) -> void:
    if actor==null or profile==null:
        return
    var z: float = actor.global_position.z+rng.randf_range(-8.0,8.0)
    var banks: Vector2=profile.banks_at_z(z)
    leaves[i]=Vector2(rng.randf_range(banks.x+0.2,banks.y-0.2),z)

func update_river(delta: float) -> void:
    if not initialized or actor==null or profile==null or flow==null or mouse_water==null:
        return
    for i in range(FOOTPRINT_COUNT):
        if not footprints[i].visible:
            continue
        footprint_lives[i]-=delta
        if footprint_lives[i]<=0.0:
            footprints[i].visible=false
        else:
            footprints[i].transparency=clampf(1.0-footprint_lives[i]/5.0,0.0,0.96)
    print_tick-=delta
    var horizontal_speed: float=Vector2(actor.velocity.x,actor.velocity.z).length()
    if mouse_water.state==MouseWaterInteraction.DRY and mouse_water.wetness>0.22 and horizontal_speed>0.45 and print_tick<=0.0 and height_sampler.is_valid():
        var slot: int=ring_cursor%FOOTPRINT_COUNT
        ring_cursor+=1
        var lateral: float=-0.09 if slot%2==0 else 0.09
        var facing: Vector3=actor.global_transform.basis.x*lateral
        var pos: Vector3=actor.global_position+facing
        var ground_y: float=float(height_sampler.call(pos.x,pos.z))
        footprints[slot].global_position=Vector3(pos.x,ground_y+0.017,pos.z)
        # Orient the print toward the actual terrain tangent plane. Otherwise
        # all footprints float as horizontal rectangles on sloped mud.
        var eps: float=0.10
        var hx: float=float(height_sampler.call(pos.x+eps,pos.z))-float(height_sampler.call(pos.x-eps,pos.z))
        var hz: float=float(height_sampler.call(pos.x,pos.z+eps))-float(height_sampler.call(pos.x,pos.z-eps))
        var surface_normal: Vector3=Vector3(-hx,2.0*eps,-hz).normalized()
        footprints[slot].quaternion=Quaternion(Vector3.UP,surface_normal)
        footprints[slot].visible=true
        footprints[slot].transparency=0.03
        footprint_lives[slot]=5.0
        print_tick=0.24
    current_tick+=delta
    if current_tick<0.15:
        return
    var time_step: float=current_tick
    current_tick=0.0
    for i in range(LEAF_COUNT):
        var leaf: Vector2=leaves[i]
        if leaf==Vector2.ZERO or leaf.distance_to(Vector2(actor.global_position.x,actor.global_position.z))>17.0:
            _respawn_leaf(i)
            leaf=leaves[i]
        var state: Dictionary=profile.sample(leaf)
        if float(state["shore_sdf"])>=0.0:
            _respawn_leaf(i)
            leaf=leaves[i]
        var stream: Vector2=flow.sample(profile,leaf)["velocity"]
        leaf+=stream*time_step*0.74
        # Streamlines may still intersect a real obstacle mesh at its center.
        # Resolve any leaf/rock overlap at the fixed S3 collider footprint.
        for rock in flow.obstacles.near(leaf,profile):
            var center: Vector2=rock["xz"]
            var radius: float=float(rock["radius"])*1.05
            var away: Vector2=leaf-center
            if away.length()<radius:
                if away.length_squared()<0.0001:
                    away=Vector2(1.0,0.0)
                leaf=center+away.normalized()*radius
        if profile.shore_distance(leaf)>=0.0:
            _respawn_leaf(i)
            leaf=leaves[i]
        leaves[i]=leaf
        var height: float=profile.surface_height(leaf.y)+0.018
        leaves_mesh.set_instance_transform(i,Transform3D(Basis(Vector3.UP,float(i)*1.7+time_step*0.25),Vector3(leaf.x,height,leaf.y)))
    for i in range(DROP_COUNT):
        var pos: Vector3=drops[i]
        var near: bool=pos.distance_to(actor.global_position)<1.2 and pos.y>actor.global_position.y-0.6
        if not near:
            if mouse_water.state==MouseWaterInteraction.DRY and mouse_water.wetness<0.25:
                pos=Vector3(0.0,-100.0,0.0)
            else:
                pos=actor.global_position+Vector3(rng.randf_range(-0.20,0.20),rng.randf_range(-0.16,0.30),rng.randf_range(-0.20,0.20))
        else:
            pos.y+=time_step*(0.28 if mouse_water.state==MouseWaterInteraction.SWIMMING else -0.46)
        drops[i]=pos
        drop_mesh.set_instance_transform(i,Transform3D(Basis.IDENTITY,pos))

func footprint_count_active() -> int:
    var n: int=0
    for part in footprints:
        if part.visible:
            n+=1
    return n
