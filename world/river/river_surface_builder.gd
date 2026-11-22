class_name RiverSurfaceBuilder
extends RefCounted
## S1 Mobile mesh: clip water geometry by 40m terrain tile, no overlapping
## per-chunk water strips and no regular straight-line bank cuts.

const ALONG_STEPS: int = 80
const ACROSS_STEPS: int = 18

func build_chunk(profile: RiverProfile, co: Vector2i, cell: float) -> ArrayMesh:
    var mesh: ArrayMesh = ArrayMesh.new()
    var x0: float = float(co.x) * cell
    var x1: float = x0 + cell
    var z0: float = float(co.y) * cell
    var vertices: PackedVector3Array = PackedVector3Array()
    var normals: PackedVector3Array = PackedVector3Array()
    var uvs: PackedVector2Array = PackedVector2Array()
    var indices: PackedInt32Array = PackedInt32Array()
    for iz in range(ALONG_STEPS + 1):
        var z: float = z0 + cell * float(iz) / float(ALONG_STEPS)
        var banks: Vector2 = profile.banks_at_z(z)
        var clipped_left: float = clampf(banks.x, x0, x1)
        var clipped_right: float = clampf(banks.y, x0, x1)
        var river_width: float = maxf(0.001, banks.y - banks.x)
        for ix in range(ACROSS_STEPS + 1):
            var t: float = float(ix) / float(ACROSS_STEPS)
            var x: float = lerpf(clipped_left, clipped_right, t)
            vertices.append(Vector3(x - x0, profile.surface_height(z), z - z0))
            normals.append(Vector3(0.0, 1.0, RiverProfile.SURFACE_GRADE).normalized())
            uvs.append(Vector2((x - banks.x) / river_width, z * 0.12))
    var row: int = ACROSS_STEPS + 1
    for iz in range(ALONG_STEPS):
        for ix in range(ACROSS_STEPS):
            var a: int = iz * row + ix
            indices.append_array(PackedInt32Array([a, a + 1, a + row, a + 1, a + row + 1, a + row]))
    var arrays: Array = []
    arrays.resize(Mesh.ARRAY_MAX)
    arrays[Mesh.ARRAY_VERTEX] = vertices
    arrays[Mesh.ARRAY_NORMAL] = normals
    arrays[Mesh.ARRAY_TEX_UV] = uvs
    arrays[Mesh.ARRAY_INDEX] = indices
    mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
    return mesh
