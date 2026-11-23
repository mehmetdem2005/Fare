class_name FareTouchInputRouter
extends Node
## One owner per finger. Touch roles never change when fingers cross the screen.
## Mouse/keyboard fallback is deliberately separate from Android multi-touch.

signal controls_changed

@export var left_handed: bool = false
@export_range(0.7, 1.6, 0.05) var joystick_size: float = 1.0
@export_range(0.15, 1.0, 0.05) var hud_opacity: float = 0.67
@export var enabled: bool = true

var joystick: FareVirtualJoystick = FareVirtualJoystick.new()
var move_touch_id: int = -1
var look_touch_id: int = -1
var action_fingers: Dictionary = {}
var pending_look: Vector2 = Vector2.ZERO
var jump_queued: bool = false
var shoulder_queued: bool = false
var recenter_queued: bool = false
var mouse_look_held: bool = false

func _ready() -> void:
    # Godot should not turn taps into duplicate mouse events on Android.
    if OS.get_name() == "Android":
        Input.emulate_mouse_from_touch = false

func _notification(what: int) -> void:
    if what == NOTIFICATION_WM_WINDOW_FOCUS_OUT:
        reset_input()

func _input(event: InputEvent) -> void:
    if not enabled:
        return
    if event is InputEventScreenTouch:
        var touch: InputEventScreenTouch = event as InputEventScreenTouch
        if touch.pressed:
            _press(touch.index, touch.position)
        else:
            _release(touch.index)
    elif event is InputEventScreenDrag:
        var drag: InputEventScreenDrag = event as InputEventScreenDrag
        if drag.index == move_touch_id:
            joystick.update(drag.position)
        elif drag.index == look_touch_id:
            # Physical-pixel delta, not viewport-scaled `relative`.
            pending_look += drag.screen_relative
    elif event is InputEventMouseButton:
        var mb: InputEventMouseButton = event as InputEventMouseButton
        if mb.button_index == MOUSE_BUTTON_RIGHT:
            mouse_look_held = mb.pressed
        elif mb.button_index == MOUSE_BUTTON_WHEEL_UP and mb.pressed:
            controls_changed.emit()
    elif event is InputEventMouseMotion and mouse_look_held:
        var mm: InputEventMouseMotion = event as InputEventMouseMotion
        pending_look += mm.screen_relative
    elif event is InputEventKey and event.pressed and not event.echo:
        var key: InputEventKey = event as InputEventKey
        if key.keycode == KEY_Q:
            shoulder_queued = true
        elif key.keycode == KEY_R:
            recenter_queued = true
        elif key.keycode == KEY_SPACE:
            jump_queued = true

func _press(finger: int, position: Vector2) -> void:
    if move_touch_id == finger or look_touch_id == finger or action_fingers.has(finger):
        return
    # Buttons have absolute priority over gameplay look.
    for action_name in ["jump", "shoulder", "recenter"]:
        if button_rect(action_name).has_point(position):
            action_fingers[finger] = action_name
            if action_name == "jump":
                jump_queued = true
            elif action_name == "shoulder":
                shoulder_queued = true
            elif action_name == "recenter":
                recenter_queued = true
            return
    var area: Rect2 = safe_viewport_rect()
    if move_touch_id == -1 and movement_region().has_point(position):
        move_touch_id = finger
        joystick.begin(position, minf(82.0, area.size.y * 0.18) * joystick_size)
    elif look_touch_id == -1 and area.has_point(position):
        look_touch_id = finger

func _release(finger: int) -> void:
    if finger == move_touch_id:
        move_touch_id = -1
        joystick.finish()
    elif finger == look_touch_id:
        look_touch_id = -1
    action_fingers.erase(finger)

func consume_look() -> Vector2:
    var result: Vector2 = pending_look
    pending_look = Vector2.ZERO
    return result

func consume_jump() -> bool:
    var result: bool = jump_queued
    jump_queued = false
    return result

func consume_shoulder_swap() -> bool:
    var result: bool = shoulder_queued
    shoulder_queued = false
    return result

func consume_recenter() -> bool:
    var result: bool = recenter_queued
    recenter_queued = false
    return result

func movement() -> Vector2:
    if move_touch_id >= 0:
        return joystick.direction
    # Keyboard fallback is useful for editor and desktop QA.
    var key_input: Vector2 = Vector2(
        float(Input.is_key_pressed(KEY_D)) - float(Input.is_key_pressed(KEY_A)),
        float(Input.is_key_pressed(KEY_S)) - float(Input.is_key_pressed(KEY_W))
    )
    return key_input.limit_length(1.0)

func look_is_active() -> bool:
    return look_touch_id >= 0 or mouse_look_held

func reset_input() -> void:
    move_touch_id = -1
    look_touch_id = -1
    action_fingers.clear()
    pending_look = Vector2.ZERO
    jump_queued = false
    shoulder_queued = false
    recenter_queued = false
    mouse_look_held = false
    joystick.finish()

func safe_viewport_rect() -> Rect2:
    var size: Vector2 = get_viewport().get_visible_rect().size
    var rect: Rect2 = Rect2(Vector2.ZERO, size)
    if OS.get_name() != "Android":
        return rect.grow(-minf(12.0, size.y * 0.025))
    var screen_size: Vector2 = Vector2(DisplayServer.screen_get_size())
    var physical: Rect2i = DisplayServer.get_display_safe_area()
    if screen_size.x <= 0.0 or screen_size.y <= 0.0 or physical.size.x <= 0 or physical.size.y <= 0:
        return rect.grow(-12.0)
    var ratio: Vector2 = Vector2(size.x / screen_size.x, size.y / screen_size.y)
    return Rect2(Vector2(physical.position) * ratio, Vector2(physical.size) * ratio).intersection(rect).grow(-8.0)

func movement_region() -> Rect2:
    var a: Rect2 = safe_viewport_rect()
    var w: float = a.size.x * 0.43
    var h: float = a.size.y * 0.68
    var left_x: float = a.position.x if not left_handed else a.end.x - w
    return Rect2(Vector2(left_x, a.end.y - h), Vector2(w, h))

func button_rect(action_name: String) -> Rect2:
    var a: Rect2 = safe_viewport_rect()
    var diameter: float = clampf(a.size.y * 0.16, 48.0, 78.0) * joystick_size
    var margin: float = maxf(14.0, a.size.y * 0.055)
    var right_side: bool = not left_handed
    var edge_x: float = a.end.x - margin - diameter * 0.5 if right_side else a.position.x + margin + diameter * 0.5
    var center: Vector2 = Vector2(edge_x, a.end.y - margin - diameter * 0.56)
    if action_name == "shoulder":
        center = Vector2(edge_x, a.position.y + margin + diameter * 0.56)
    elif action_name == "recenter":
        var offset: float = diameter + 10.0
        center = Vector2(edge_x - offset if right_side else edge_x + offset,
            a.position.y + margin + diameter * 0.56)
    return Rect2(center - Vector2.ONE * diameter * 0.5, Vector2.ONE * diameter)
