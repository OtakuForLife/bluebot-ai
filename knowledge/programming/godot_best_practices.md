# Godot Engine Best Practices

## Project Structure

### Recommended Directory Layout
```
project/
├── scenes/          # .tscn scene files
│   ├── characters/
│   ├── levels/
│   ├── ui/
│   └── main.tscn
├── scripts/         # .gd script files
│   ├── autoload/    # Singleton scripts
│   ├── components/  # Reusable components
│   └── utils/       # Helper functions
├── assets/          # Game assets
│   ├── sprites/
│   ├── models/
│   ├── audio/
│   └── fonts/
├── resources/       # .tres resource files
└── addons/          # Third-party plugins
```

### Naming Conventions
- **Scenes**: `PascalCase.tscn` (e.g., `PlayerCharacter.tscn`)
- **Scripts**: `snake_case.gd` (e.g., `player_controller.gd`)
- **Variables**: `snake_case` (e.g., `player_health`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_SPEED`)
- **Functions**: `snake_case` (e.g., `calculate_damage()`)
- **Signals**: `snake_case` (e.g., `health_changed`)
- **Classes**: `PascalCase` (e.g., `class_name PlayerController`)

## GDScript Best Practices

### Script Organization
```gdscript
# 1. Class declaration
class_name PlayerController
extends CharacterBody2D

# 2. Signals
signal health_changed(new_health)
signal died

# 3. Enums
enum State { IDLE, WALKING, JUMPING, FALLING }

# 4. Constants
const MAX_HEALTH = 100
const SPEED = 200.0

# 5. Exported variables
@export var jump_force: float = 400.0
@export var gravity: float = 980.0

# 6. Public variables
var current_health: int = MAX_HEALTH
var current_state: State = State.IDLE

# 7. Private variables (prefix with _)
var _velocity: Vector2 = Vector2.ZERO

# 8. Onready variables
@onready var sprite: Sprite2D = $Sprite2D
@onready var animation_player: AnimationPlayer = $AnimationPlayer

# 9. Built-in virtual methods (_ready, _process, etc.)
func _ready() -> void:
    pass

func _physics_process(delta: float) -> void:
    pass

# 10. Public methods
func take_damage(amount: int) -> void:
    pass

# 11. Private methods (prefix with _)
func _update_animation() -> void:
    pass
```

### Type Hints
Always use type hints for better performance and error detection:

```gdscript
# Good
func calculate_damage(base_damage: int, multiplier: float) -> int:
    return int(base_damage * multiplier)

var player_name: String = "Hero"
var health: int = 100
var speed: float = 5.0

# Avoid
func calculate_damage(base_damage, multiplier):
    return base_damage * multiplier

var player_name = "Hero"
```

### Signals
Use signals for decoupled communication:

```gdscript
# Define signal
signal enemy_defeated(enemy_type: String, reward: int)

# Emit signal
enemy_defeated.emit("goblin", 50)

# Connect signal
enemy.enemy_defeated.connect(_on_enemy_defeated)

func _on_enemy_defeated(enemy_type: String, reward: int) -> void:
    print("Defeated: ", enemy_type, " Reward: ", reward)
```

### Node References
Prefer `@onready` over `get_node()` in `_ready()`:

```gdscript
# Good
@onready var health_bar: ProgressBar = $UI/HealthBar
@onready var sprite: Sprite2D = $Sprite2D

# Less efficient
var health_bar: ProgressBar
var sprite: Sprite2D

func _ready() -> void:
    health_bar = $UI/HealthBar
    sprite = $Sprite2D
```

### Resource Management
Use `preload()` for resources needed at startup, `load()` for runtime:

```gdscript
# Preload - loaded at compile time
const BULLET_SCENE = preload("res://scenes/bullet.tscn")

# Load - loaded at runtime
var enemy_scene = load("res://scenes/enemy.tscn")
```

## Performance Optimization

### Physics Process vs Process
- Use `_physics_process()` for physics and movement
- Use `_process()` for visual updates and non-physics logic

```gdscript
func _physics_process(delta: float) -> void:
    # Movement, collision detection
    velocity = calculate_velocity(delta)
    move_and_slide()

func _process(delta: float) -> void:
    # Visual updates, UI, animations
    update_health_bar()
```

### Object Pooling
Reuse objects instead of creating/destroying:

```gdscript
var bullet_pool: Array[Node] = []
const POOL_SIZE = 20

func _ready() -> void:
    # Pre-create bullets
    for i in POOL_SIZE:
        var bullet = BULLET_SCENE.instantiate()
        bullet.visible = false
        add_child(bullet)
        bullet_pool.append(bullet)

func get_bullet() -> Node:
    for bullet in bullet_pool:
        if not bullet.visible:
            bullet.visible = true
            return bullet
    return null

func return_bullet(bullet: Node) -> void:
    bullet.visible = false
    bullet.position = Vector2.ZERO
```

### Avoid Expensive Operations in Loops
```gdscript
# Bad - get_node() called every frame
func _process(delta: float) -> void:
    for enemy in get_tree().get_nodes_in_group("enemies"):
        enemy.update()

# Good - cache the array
@onready var enemies: Array = []

func _ready() -> void:
    enemies = get_tree().get_nodes_in_group("enemies")

func _process(delta: float) -> void:
    for enemy in enemies:
        enemy.update()
```

## Scene Design

### Composition Over Inheritance
Build complex objects from simple components:

```gdscript
# Component-based design
# HealthComponent.gd
class_name HealthComponent
extends Node

signal health_changed(current, maximum)
signal died

@export var max_health: int = 100
var current_health: int

func take_damage(amount: int) -> void:
    current_health -= amount
    health_changed.emit(current_health, max_health)
    if current_health <= 0:
        died.emit()
```

### Scene Instancing
Use scene instancing for reusable objects:

```gdscript
# Spawn enemy
var enemy = ENEMY_SCENE.instantiate()
enemy.position = spawn_position
add_child(enemy)

# Clean up when done
enemy.queue_free()
```

## Input Handling

### Use Input Actions
Define input actions in Project Settings, not hardcoded keys:

```gdscript
# Good - uses input map
func _process(delta: float) -> void:
    if Input.is_action_pressed("move_right"):
        move_right()
    if Input.is_action_just_pressed("jump"):
        jump()

# Avoid - hardcoded keys
func _process(delta: float) -> void:
    if Input.is_key_pressed(KEY_D):
        move_right()
```

### Input Buffering
Buffer inputs for responsive controls:

```gdscript
var jump_buffer_time: float = 0.1
var jump_buffer_timer: float = 0.0

func _process(delta: float) -> void:
    if Input.is_action_just_pressed("jump"):
        jump_buffer_timer = jump_buffer_time
    
    if jump_buffer_timer > 0:
        jump_buffer_timer -= delta
        if can_jump():
            jump()
            jump_buffer_timer = 0
```

## Error Handling

### Null Checks
Always check for null before using nodes:

```gdscript
func attack_target(target: Node2D) -> void:
    if target == null:
        push_warning("Attack target is null")
        return
    
    target.take_damage(damage)
```

### Assertions
Use assertions for debugging:

```gdscript
func set_health(value: int) -> void:
    assert(value >= 0, "Health cannot be negative")
    assert(value <= max_health, "Health exceeds maximum")
    current_health = value
```

## Autoload (Singletons)

Use autoload for global managers:

```gdscript
# GameManager.gd (autoload)
extends Node

var score: int = 0
var current_level: int = 1

func add_score(points: int) -> void:
    score += points
    
func load_level(level_number: int) -> void:
    current_level = level_number
    get_tree().change_scene_to_file("res://scenes/level_%d.tscn" % level_number)

# Access from any script
GameManager.add_score(100)
```

## Common Patterns

### State Machine
```gdscript
enum State { IDLE, WALK, JUMP, ATTACK }
var current_state: State = State.IDLE

func _physics_process(delta: float) -> void:
    match current_state:
        State.IDLE:
            process_idle(delta)
        State.WALK:
            process_walk(delta)
        State.JUMP:
            process_jump(delta)
        State.ATTACK:
            process_attack(delta)

func change_state(new_state: State) -> void:
    exit_state(current_state)
    current_state = new_state
    enter_state(new_state)
```

### Observer Pattern (Signals)
```gdscript
# Subject
signal value_changed(new_value)

func set_value(value: int) -> void:
    _value = value
    value_changed.emit(value)

# Observer
func _ready() -> void:
    subject.value_changed.connect(_on_value_changed)

func _on_value_changed(new_value: int) -> void:
    print("Value changed to: ", new_value)
```

## Testing and Debugging

### Debug Prints
```gdscript
# Use push_warning for warnings
push_warning("Player health is low: %d" % health)

# Use push_error for errors
push_error("Failed to load scene: %s" % scene_path)

# Use print_debug for debug info
print_debug("Player position: ", position)
```

### Remote Debugging
Enable remote scene tree and inspector in Project Settings for live debugging.

## Resources

- Official Godot Documentation: https://docs.godotengine.org
- GDScript Style Guide: https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/gdscript_styleguide.html
- Godot Best Practices: https://docs.godotengine.org/en/stable/tutorials/best_practices/

