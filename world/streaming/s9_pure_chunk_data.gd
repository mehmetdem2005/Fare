class_name S9PureChunkData
extends RefCounted
## Isolated CPU-only chunk data. No SceneTree, ArrayMesh, physics shape,
## RenderingServer, ImageTexture or shared Resource in the worker.
## All helper resources are created privately inside build().
const CELL: float=40.0
const GRID: int=56
const FLOW_RESOLUTION: int=32
var co: Vector2i
var terrain_arrays: Array=[]
var water_arrays: Array=[]
var flow_rgba8: PackedByteArray=PackedByteArray()
var worker_elapsed_ms: float=0.0
var completed: bool=false

func _base_height(x: float,z: float,hnoise: FastNoiseLite,dnoise: FastNoiseLite) -> float:
    var valley: float=2.0+hnoise.get_noise_2d(x,z)*2.5+dnoise.get_noise_2d(x,z)*0.4
    var mountain_factor: float=smoothstep(30.0,110.0,absf(x))
    var mountain: float=12.0*mountain_factor+pow(mountain_factor,1.55)*(13.0+absf(hnoise.get_noise_2d(x+91.0,z))*20.0)
    return valley+mountain

func _height(x: float,z: float,profile: RiverProfile,hnoise: FastNoiseLite,dnoise: FastNoiseLite) -> float:
    var base_y: float=_base_height(x,z,hnoise,dnoise)
    if absf(x)>45.0:
        return base_y
    return profile.terrain_height(x,z,base_y)

func _x_grid(chunk_x: float) -> PackedFloat32Array:
    var values: PackedFloat32Array=PackedFloat32Array([0.0])
    var local_x: float=0.0
    while local_x<CELL-0.0001:
        var world_x: float=chunk_x+local_x
        var step: float=0.38 if absf(world_x)<=22.0 else 1.42
        local_x=minf(CELL,local_x+step)
        values.append(local_x)
    return values

func _terrain(origin: Vector3,profile: RiverProfile,substrate: ShoreSubstrate,hnoise: FastNoiseLite,dnoise: FastNoiseLite) -> Array:
    var verts: PackedVector3Array=PackedVector3Array()
    var normals: PackedVector3Array=PackedVector3Array()
    var uv: PackedVector2Array=PackedVector2Array()
    var uv2: PackedVector2Array=PackedVector2Array()
    var colors: PackedColorArray=PackedColorArray()
    var indices: PackedInt32Array=PackedInt32Array()
    var x_grid: PackedFloat32Array=_x_grid(origin.x)
    var columns: int=x_grid.size()
    var rows: int=GRID+1
    var dz: float=CELL/float(GRID)
    for iz in range(rows):
        for ix in range(columns):
            var lx: float=x_grid[ix]
            var lz: float=float(iz)*dz
            var wx: float=origin.x+lx
            var wz: float=origin.z+lz
            var base_y: float=_base_height(wx,wz,hnoise,dnoise)
            if absf(wx)>45.0:
                verts.append(Vector3(lx,base_y,lz))
                uv.append(Vector2(wx,wz)*0.1)
                uv2.append(Vector2.ZERO)
                var macro: float=substrate.macro.get_noise_2d(wx,wz)
                var forest_cover: float=clampf(0.31+0.15*macro,0.0,0.52)
                colors.append(Color(0.0,0.0,0.0,forest_cover))
            else:
                var info: Dictionary=profile.ground_sample(Vector2(wx,wz),base_y)
                verts.append(Vector3(lx,float(info["terrain_y"]),lz))
                uv.append(Vector2(wx,wz)*0.1)
                uv2.append(Vector2(maxf(0.0,float(info["depth"])),0.0))
                var sediment: Dictionary=substrate.sample(info,Vector2(wx,wz))
                colors.append(Color(float(sediment["gravel"]),float(sediment["wetness"]),float(sediment["silt"]),float(sediment["forest"])))
    for iz in range(rows):
        for ix in range(columns):
            var ix0: int=maxi(ix-1,0)
            var ix1: int=mini(ix+1,columns-1)
            var iz0: int=maxi(iz-1,0)
            var iz1: int=mini(iz+1,rows-1)
            var dx_vec: Vector3=verts[iz*columns+ix1]-verts[iz*columns+ix0]
            var dz_vec: Vector3=verts[iz1*columns+ix]-verts[iz0*columns+ix]
            var n: Vector3=dz_vec.cross(dx_vec).normalized()
            if ix==0 or ix==columns-1 or iz==0 or iz==rows-1:
                var v: Vector3=verts[iz*columns+ix]
                var wx: float=origin.x+v.x
                var wz: float=origin.z+v.z
                var slope_x: float=_height(wx+0.2,wz,profile,hnoise,dnoise)-_height(wx-0.2,wz,profile,hnoise,dnoise)
                var slope_z: float=_height(wx,wz+0.2,profile,hnoise,dnoise)-_height(wx,wz-0.2,profile,hnoise,dnoise)
                n=Vector3(-slope_x,0.4,-slope_z).normalized()
            normals.append(n)
            var metadata: Vector2=uv2[iz*columns+ix]
            uv2[iz*columns+ix]=Vector2(metadata.x,clampf(0.97-0.10*(1.0-n.y),0.84,1.0))
    for iz in range(GRID):
        for ix in range(columns-1):
            var a: int=iz*columns+ix
            indices.append(a)
            indices.append(a+1)
            indices.append(a+columns)
            indices.append(a+1)
            indices.append(a+columns+1)
            indices.append(a+columns)
    var arrays: Array=[]
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX]=verts
    arrays[Mesh.ARRAY_NORMAL]=normals
    arrays[Mesh.ARRAY_TEX_UV]=uv
    arrays[Mesh.ARRAY_TEX_UV2]=uv2
    arrays[Mesh.ARRAY_COLOR]=colors
    arrays[Mesh.ARRAY_INDEX]=indices
    return arrays

func _water(origin: Vector3,profile: RiverProfile) -> Array:
    var verts: PackedVector3Array=PackedVector3Array()
    var normals: PackedVector3Array=PackedVector3Array()
    var uvs: PackedVector2Array=PackedVector2Array()
    var indices: PackedInt32Array=PackedInt32Array()
    var x0: float=origin.x
    var x1: float=x0+CELL
    var z0: float=origin.z
    for iz in range(RiverSurfaceBuilder.ALONG_STEPS+1):
        var z: float=z0+CELL*float(iz)/float(RiverSurfaceBuilder.ALONG_STEPS)
        var banks: Vector2=profile.banks_at_z(z)
        var clipped_left: float=clampf(banks.x,x0,x1)
        var clipped_right: float=clampf(banks.y,x0,x1)
        var river_width: float=maxf(0.001,banks.y-banks.x)
        for ix in range(RiverSurfaceBuilder.ACROSS_STEPS+1):
            var t: float=float(ix)/float(RiverSurfaceBuilder.ACROSS_STEPS)
            var x: float=lerpf(clipped_left,clipped_right,t)
            verts.append(Vector3(x-x0,profile.surface_height(z),z-z0))
            normals.append(Vector3(0.0,1.0,RiverProfile.SURFACE_GRADE).normalized())
            uvs.append(Vector2((x-banks.x)/river_width,z*0.12))
    var row: int=RiverSurfaceBuilder.ACROSS_STEPS+1
    for iz in range(RiverSurfaceBuilder.ALONG_STEPS):
        for ix in range(RiverSurfaceBuilder.ACROSS_STEPS):
            var a: int=iz*row+ix
            indices.append(a)
            indices.append(a+1)
            indices.append(a+row)
            indices.append(a+1)
            indices.append(a+row+1)
            indices.append(a+row)
    var arrays: Array=[]
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX]=verts
    arrays[Mesh.ARRAY_NORMAL]=normals
    arrays[Mesh.ARRAY_TEX_UV]=uvs
    arrays[Mesh.ARRAY_INDEX]=indices
    return arrays

func _flow(origin: Vector3,profile: RiverProfile,field: RiverFlowField) -> PackedByteArray:
    var pixels: PackedByteArray=PackedByteArray()
    pixels.resize(FLOW_RESOLUTION*FLOW_RESOLUTION*4)
    var stride: float=CELL/float(FLOW_RESOLUTION-1)
    for iy in range(FLOW_RESOLUTION):
        for ix in range(FLOW_RESOLUTION):
            var position: Vector2=Vector2(origin.x,origin.z)+Vector2(float(ix),float(iy))*stride
            var sample: Dictionary=field.sample(profile,position)
            var v: Vector2=sample["velocity"]
            var color: Color=Color(
                clampf(0.5+v.x/(2.0*RiverFlowField.MAX_VECTOR_MPS),0.0,1.0),
                clampf(0.5+v.y/(2.0*RiverFlowField.MAX_VECTOR_MPS),0.0,1.0),
                clampf(float(sample["turbulence"]),0.0,1.0),
                clampf(float(sample["foam"]),0.0,1.0))
            var rgba: int=color.to_rgba32()
            var k: int=(iy*FLOW_RESOLUTION+ix)*4
            pixels[k]=(rgba>>24)&255
            pixels[k+1]=(rgba>>16)&255
            pixels[k+2]=(rgba>>8)&255
            pixels[k+3]=rgba&255
    return pixels

func build() -> void:
    var began_usec: int=Time.get_ticks_usec()
    var profile: RiverProfile=RiverProfile.new()
    var substrate: ShoreSubstrate=ShoreSubstrate.new()
    var height_noise: FastNoiseLite=FastNoiseLite.new()
    height_noise.seed=49825
    height_noise.noise_type=FastNoiseLite.TYPE_SIMPLEX_SMOOTH
    height_noise.frequency=0.014
    height_noise.fractal_type=FastNoiseLite.FRACTAL_FBM
    height_noise.fractal_octaves=4
    var detail_noise: FastNoiseLite=FastNoiseLite.new()
    detail_noise.seed=29608
    detail_noise.frequency=0.054
    var origin: Vector3=Vector3(float(co.x)*CELL,0.0,float(co.y)*CELL)
    terrain_arrays=_terrain(origin,profile,substrate,height_noise,detail_noise)
    if co.x>=-1 and co.x<=0:
        water_arrays=_water(origin,profile)
        flow_rgba8=_flow(origin,profile,RiverFlowField.new())
    worker_elapsed_ms=float(Time.get_ticks_usec()-began_usec)*0.001
    completed=true

func create_terrain_mesh() -> ArrayMesh:
    var mesh: ArrayMesh=ArrayMesh.new()
    mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,terrain_arrays)
    return mesh

func create_water_mesh() -> ArrayMesh:
    var mesh: ArrayMesh=ArrayMesh.new()
    mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,water_arrays)
    return mesh

func create_flow_image() -> Image:
    return Image.create_from_data(FLOW_RESOLUTION,FLOW_RESOLUTION,false,Image.FORMAT_RGBA8,flow_rgba8)
