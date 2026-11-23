class_name FareTouchHUD
extends Control
## Draw-only touch overlay. The router owns ALL touches (no Control stealing).
var router: FareTouchInputRouter
var captions: Dictionary = {"jump": "JUMP", "shoulder": "SIDE", "recenter": "CAM"}

func _ready() -> void:
    mouse_filter = Control.MOUSE_FILTER_IGNORE
    set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

func _process(_delta: float) -> void:
    queue_redraw()

func _draw() -> void:
    if router == null:
        return
    var safe: Rect2 = router.safe_viewport_rect()
    var alpha: float = router.hud_opacity
    var visual_radius: float = clampf(safe.size.y * 0.18, 45.0, 82.0) * router.joystick_size
    var origin: Vector2 = Vector2(safe.position.x + 24.0 + visual_radius,
        safe.end.y - 22.0 - visual_radius)
    if router.left_handed:
        origin.x = safe.end.x - 24.0 - visual_radius
    if router.joystick.active:
        origin = router.joystick.center
    draw_circle(origin, visual_radius, Color(0.04, 0.08, 0.11, 0.21 * alpha))
    draw_arc(origin, visual_radius, 0.0, TAU, 64, Color(0.80, 0.87, 0.87, 0.58 * alpha), 2.0, true)
    draw_circle(router.joystick.knob if router.joystick.active else origin,
        visual_radius * 0.42, Color(0.72, 0.83, 0.82, (0.67 if router.joystick.active else 0.33) * alpha))
    for button_name in captions.keys():
        var rect: Rect2 = router.button_rect(button_name)
        var center: Vector2 = rect.get_center()
        var pressed: bool = router.action_fingers.values().has(button_name)
        draw_circle(center, rect.size.x * 0.5, Color(0.05, 0.11, 0.13, (0.46 if pressed else 0.22) * alpha))
        draw_arc(center, rect.size.x * 0.5, 0.0, TAU, 48,
            Color(0.77, 0.88, 0.85, 0.79 * alpha), 2.0, true)
        var font: Font = ThemeDB.fallback_font
        if font != null:
            var label: String = captions[button_name]
            var font_size: int = clampi(int(rect.size.x * 0.22), 10, 18)
            var width: float = font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
            draw_string(font, center + Vector2(-width * 0.5, font_size * 0.36),
                label, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(0.94, 0.97, 0.92, alpha))
