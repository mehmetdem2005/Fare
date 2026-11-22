class_name WaterQualitySettings
extends RefCounted
## S4 explicit water-quality presets. Android profiling (S8) decides thresholds.
const LOW: int = 0
const BALANCED: int = 1
const HIGH: int = 2

func configure(material: ShaderMaterial, level: int) -> void:
    # Low skips distorted depth lookups and makes caustic emission zero.
    # Screen depth read still happens for absorption; renderer may retain
    # full-screen copy cost. Measure GPU on device before declaring savings.
    if level <= LOW:
        material.set_shader_parameter("enable_refraction",false)
        material.set_shader_parameter("enable_caustics",false)
        material.set_shader_parameter("refraction_strength",0.0)
        material.set_shader_parameter("caustic_strength",0.0)
        material.set_shader_parameter("wave_strength",0.55)
    elif level >= HIGH:
        material.set_shader_parameter("enable_refraction",true)
        material.set_shader_parameter("enable_caustics",true)
        material.set_shader_parameter("refraction_strength",0.62)
        material.set_shader_parameter("caustic_strength",0.34)
        material.set_shader_parameter("wave_strength",0.98)
    else:
        material.set_shader_parameter("enable_refraction",true)
        material.set_shader_parameter("enable_caustics",true)
        material.set_shader_parameter("refraction_strength",0.42)
        material.set_shader_parameter("caustic_strength",0.22)
        material.set_shader_parameter("wave_strength",0.80)
