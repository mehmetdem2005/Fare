class_name FareVirtualJoystick
extends RefCounted
## Deterministic radial deadzone and nonlinear response for floating touch input.

var active: bool = false
var center: Vector2 = Vector2.ZERO
var knob: Vector2 = Vector2.ZERO
var direction: Vector2 = Vector2.ZERO
var radius: float = 62.0
var deadzone: float = 0.12
var response_exponent: float = 1.35

func begin(at: Vector2, joystick_radius: float) -> void:
    active = true
    center = at
    knob = at
    radius = maxf(20.0, joystick_radius)
    direction = Vector2.ZERO

func update(at: Vector2) -> Vector2:
    if not active:
        return Vector2.ZERO
    var displacement: Vector2 = at - center
    var normalized: Vector2 = displacement / radius
    var magnitude: float = minf(normalized.length(), 1.0)
    knob = center + normalized.limit_length(1.0) * radius
    if magnitude <= deadzone:
        direction = Vector2.ZERO
        return direction
    var adjusted: float = clampf((magnitude - deadzone) / (1.0 - deadzone), 0.0, 1.0)
    direction = normalized.normalized() * pow(adjusted, response_exponent)
    return direction

func finish() -> void:
    active = false
    direction = Vector2.ZERO
    knob = center
