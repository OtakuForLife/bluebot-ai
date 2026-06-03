# Game Code Architecture Patterns

## SOLID Principles in Game Development

### Single Responsibility Principle (SRP)
Each class/script should have one clear purpose:

```gdscript
# Good - Single responsibility
class_name HealthComponent
extends Node

var max_health: int = 100
var current_health: int

func take_damage(amount: int) -> void:
    current_health = max(0, current_health - amount)

func heal(amount: int) -> void:
    current_health = min(max_health, current_health + amount)

# Bad - Multiple responsibilities
class_name Player
extends CharacterBody2D

var health: int
var inventory: Array
var quest_log: Array

func take_damage(amount: int) -> void: pass
func add_item(item) -> void: pass
func complete_quest(quest_id) -> void: pass
func render_ui() -> void: pass  # Too many responsibilities!
```

### Open/Closed Principle
Open for extension, closed for modification:

```gdscript
# Base weapon class
class_name Weapon
extends Node2D

func attack() -> void:
    pass  # Override in subclasses

# Extend without modifying base
class_name Sword
extends Weapon

func attack() -> void:
    # Sword-specific attack
    pass

class_name Bow
extends Weapon

func attack() -> void:
    # Bow-specific attack
    pass
```

### Dependency Inversion
Depend on abstractions, not concrete implementations:

```gdscript
# Abstract interface
class_name IMovementController
extends Node

func move(direction: Vector2) -> void:
    pass

# Concrete implementations
class_name PlayerMovement
extends IMovementController

func move(direction: Vector2) -> void:
    # Player-specific movement
    pass

class_name AIMovement
extends IMovementController

func move(direction: Vector2) -> void:
    # AI-specific movement
    pass
```

## Component-Based Architecture

### Entity-Component Pattern
Break down game objects into reusable components:

```gdscript
# Entity (Player scene)
# - HealthComponent
# - MovementComponent
# - AttackComponent
# - InventoryComponent

# HealthComponent.gd
class_name HealthComponent
extends Node

signal health_changed(current, max)
signal died

@export var max_health: int = 100
var current_health: int

func _ready() -> void:
    current_health = max_health

func take_damage(amount: int) -> void:
    current_health -= amount
    health_changed.emit(current_health, max_health)
    if current_health <= 0:
        died.emit()

# MovementComponent.gd
class_name MovementComponent
extends Node

@export var speed: float = 200.0
@export var acceleration: float = 1000.0

var velocity: Vector2 = Vector2.ZERO

func move(direction: Vector2, delta: float) -> Vector2:
    var target_velocity = direction * speed
    velocity = velocity.move_toward(target_velocity, acceleration * delta)
    return velocity
```

### Using Components
```gdscript
# Player.gd
class_name Player
extends CharacterBody2D

@onready var health: HealthComponent = $HealthComponent
@onready var movement: MovementComponent = $MovementComponent

func _ready() -> void:
    health.died.connect(_on_died)

func _physics_process(delta: float) -> void:
    var input_dir = Input.get_vector("left", "right", "up", "down")
    velocity = movement.move(input_dir, delta)
    move_and_slide()

func _on_died() -> void:
    queue_free()
```

## Design Patterns

### Singleton Pattern (Autoload)
Global managers for game-wide systems:

```gdscript
# GameManager.gd (Autoload as "GameManager")
extends Node

var player: Player
var current_level: int = 1
var score: int = 0

signal score_changed(new_score)

func add_score(points: int) -> void:
    score += points
    score_changed.emit(score)

func reset_game() -> void:
    score = 0
    current_level = 1
    get_tree().reload_current_scene()

# Access from anywhere
GameManager.add_score(100)
```

### Observer Pattern (Signals)
Decouple communication between objects:

```gdscript
# Publisher
class_name Enemy
extends CharacterBody2D

signal died(enemy_type: String, position: Vector2)

func take_damage(amount: int) -> void:
    health -= amount
    if health <= 0:
        died.emit(enemy_type, global_position)
        queue_free()

# Subscriber
class_name LootManager
extends Node

func _ready() -> void:
    for enemy in get_tree().get_nodes_in_group("enemies"):
        enemy.died.connect(_on_enemy_died)

func _on_enemy_died(enemy_type: String, position: Vector2) -> void:
    spawn_loot(enemy_type, position)
```

### Factory Pattern
Create objects without specifying exact class:

```gdscript
# EnemyFactory.gd
class_name EnemyFactory
extends Node

const GOBLIN = preload("res://scenes/enemies/goblin.tscn")
const ORC = preload("res://scenes/enemies/orc.tscn")
const DRAGON = preload("res://scenes/enemies/dragon.tscn")

enum EnemyType { GOBLIN, ORC, DRAGON }

func create_enemy(type: EnemyType) -> Enemy:
    var enemy: Enemy
    match type:
        EnemyType.GOBLIN:
            enemy = GOBLIN.instantiate()
        EnemyType.ORC:
            enemy = ORC.instantiate()
        EnemyType.DRAGON:
            enemy = DRAGON.instantiate()
    return enemy

# Usage
var factory = EnemyFactory.new()
var goblin = factory.create_enemy(EnemyFactory.EnemyType.GOBLIN)
add_child(goblin)
```

### Object Pool Pattern
Reuse objects for performance:

```gdscript
# ObjectPool.gd
class_name ObjectPool
extends Node

var pool: Array[Node] = []
var scene: PackedScene
var pool_size: int

func _init(scene_path: String, size: int) -> void:
    scene = load(scene_path)
    pool_size = size
    _create_pool()

func _create_pool() -> void:
    for i in pool_size:
        var obj = scene.instantiate()
        obj.set_process(false)
        obj.visible = false
        add_child(obj)
        pool.append(obj)

func get_object() -> Node:
    for obj in pool:
        if not obj.visible:
            obj.visible = true
            obj.set_process(true)
            return obj
    # Pool exhausted, create new
    var obj = scene.instantiate()
    add_child(obj)
    pool.append(obj)
    return obj

func return_object(obj: Node) -> void:
    obj.visible = false
    obj.set_process(false)
    obj.position = Vector2.ZERO
```

### State Pattern
Manage complex state transitions:

```gdscript
# State.gd (Base class)
class_name State
extends Node

func enter() -> void:
    pass

func exit() -> void:
    pass

func update(delta: float) -> void:
    pass

func physics_update(delta: float) -> void:
    pass

# IdleState.gd
class_name IdleState
extends State

@export var player: Player

func enter() -> void:
    player.animation_player.play("idle")

func update(delta: float) -> void:
    if Input.is_action_pressed("move"):
        player.state_machine.change_state("walk")

# StateMachine.gd
class_name StateMachine
extends Node

var states: Dictionary = {}
var current_state: State

func _ready() -> void:
    for child in get_children():
        if child is State:
            states[child.name.to_lower()] = child

func change_state(state_name: String) -> void:
    if current_state:
        current_state.exit()
    current_state = states.get(state_name)
    if current_state:
        current_state.enter()

func _process(delta: float) -> void:
    if current_state:
        current_state.update(delta)
```

### Command Pattern
Encapsulate actions for undo/redo:

```gdscript
# Command.gd
class_name Command
extends RefCounted

func execute() -> void:
    pass

func undo() -> void:
    pass

# MoveCommand.gd
class_name MoveCommand
extends Command

var actor: Node2D
var old_position: Vector2
var new_position: Vector2

func _init(actor_node: Node2D, target_pos: Vector2) -> void:
    actor = actor_node
    old_position = actor.position
    new_position = target_pos

func execute() -> void:
    actor.position = new_position

func undo() -> void:
    actor.position = old_position

# CommandManager.gd
class_name CommandManager
extends Node

var history: Array[Command] = []
var current_index: int = -1

func execute_command(command: Command) -> void:
    command.execute()
    # Clear redo history
    history = history.slice(0, current_index + 1)
    history.append(command)
    current_index += 1

func undo() -> void:
    if current_index >= 0:
        history[current_index].undo()
        current_index -= 1

func redo() -> void:
    if current_index < history.size() - 1:
        current_index += 1
        history[current_index].execute()
```

## Separation of Concerns

### MVC Pattern (Model-View-Controller)
```gdscript
# Model - Data and logic
class_name PlayerModel
extends RefCounted

var health: int = 100
var max_health: int = 100
var score: int = 0

signal health_changed(current, max)
signal score_changed(new_score)

func take_damage(amount: int) -> void:
    health = max(0, health - amount)
    health_changed.emit(health, max_health)

func add_score(points: int) -> void:
    score += points
    score_changed.emit(score)

# View - Presentation
class_name PlayerView
extends Control

@onready var health_bar: ProgressBar = $HealthBar
@onready var score_label: Label = $ScoreLabel

func update_health(current: int, maximum: int) -> void:
    health_bar.value = (float(current) / maximum) * 100

func update_score(new_score: int) -> void:
    score_label.text = "Score: %d" % new_score

# Controller - Connects Model and View
class_name PlayerController
extends Node

var model: PlayerModel
var view: PlayerView

func _ready() -> void:
    model = PlayerModel.new()
    view = $PlayerView
    
    model.health_changed.connect(view.update_health)
    model.score_changed.connect(view.update_score)
```

## Best Practices

1. **Keep Scripts Small**: Aim for < 200 lines per script
2. **Use Composition**: Prefer components over deep inheritance
3. **Minimize Coupling**: Use signals instead of direct references
4. **Encapsulate Data**: Use getters/setters for important properties
5. **Document Interfaces**: Comment public methods and signals
6. **Test in Isolation**: Design components to be testable independently

## Resources

- *Game Programming Patterns* by Robert Nystrom
- *Clean Code* by Robert C. Martin
- Godot Design Patterns documentation

