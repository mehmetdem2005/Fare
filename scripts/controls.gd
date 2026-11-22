extends Control

# Coordinates use VIEWPORT pixels, not physical screen pixels.
var joystick: Vector2 = Vector2.ZERO
var stamina: float = 100.0
var speed: float = 0.0
var chunk_count: int = 0
var jumping: bool = false
var sprinting: bool = false
var rig_status: String = "?"
var message: String = ""
var build_tag: String = "S8"

func _ready() -> void:
    mouse_filter = Control.MOUSE_FILTER_IGNORE
    set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

func stick_center() -> Vector2:
    var size: Vector2 = get_viewport_rect().size
    return Vector2(size.x * 0.12, size.y * 0.80)

func jump_center() -> Vector2:
    var size: Vector2 = get_viewport_rect().size
    return Vector2(size.x * 0.89, size.y * 0.80)

func run_center() -> Vector2:
    var size: Vector2 = get_viewport_rect().size
    return Vector2(size.x * 0.78, size.y * 0.83)

func stick_radius() -> float:
    return minf(get_viewport_rect().size.y * 0.11, 88.0)

func button_radius() -> float:
    return minf(get_viewport_rect().size.y * 0.08, 60.0)

func _process(_delta: float) -> void:
    queue_redraw()

func _draw() -> void:
    var s: Vector2 = get_viewport_rect().size
    var center: Vector2 = stick_center()
    var radius: float = stick_radius()
    draw_circle(center, radius, Color(0.03, 0.09, 0.12, 0.35))
    draw_arc(center, radius, 0.0, TAU, 64, Color(0.89, 0.95, 0.97, 0.57), 2.4, true)
    draw_circle(center + Vector2(joystick.x, -joystick.y) * radius * 0.52, radius * 0.34, Color(0.92, 0.97, 0.99, 0.72))
    _button(run_center(), button_radius() * 0.90, "KOS", sprinting)
    _button(jump_center(), button_radius(), "ZIPLA", jumping)
    draw_rect(Rect2(20.0, 18.0, 225.0, 74.0), Color(0.02, 0.09, 0.11, 0.69), true)
    draw_rect(Rect2(32.0, 53.0, 200.0, 8.0), Color(0.06, 0.08, 0.07, 0.75), true)
    draw_rect(Rect2(32.0, 53.0, 200.0 * clampf(stamina / 100.0, 0.0, 1.0), 8.0), Color(0.51, 0.82, 0.49), true)
    _label(Vector2(32.0, 41.0), "STAMINA", 17, Color.WHITE)
    _label(Vector2(32.0, 79.0), "CHUNK %d  %.1f m/s" % [chunk_count, speed], 13, Color(0.93, 0.98, 0.93))
    _label(Vector2(s.x * 0.5 - 95.0, 34.0), "FARE VADISI " + build_tag, 19, Color.WHITE)
    _label(Vector2(s.x * 0.5 - 115.0, 56.0), "RIG: %s" % rig_status, 13, Color(0.93, 0.98, 0.94))
    if not message.is_empty():
        _label(Vector2(s.x * 0.35, 85.0), message, 15, Color(1.0, 0.85, 0.61))

func _button(pos: Vector2, r: float, text: String, active: bool) -> void:
    draw_circle(pos, r, Color(0.15, 0.34, 0.29, 0.92) if active else Color(0.04, 0.18, 0.18, 0.75))
    draw_arc(pos, r, 0.0, TAU, 44, Color(0.91, 0.96, 0.89, 0.72), 2.0, true)
    _label(pos + Vector2(-r * 0.40, 6.0), text, 16, Color.WHITE)

func _label(pos: Vector2, text: String, size: int, color: Color) -> void:
    draw_string(ThemeDB.fallback_font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size, color)
