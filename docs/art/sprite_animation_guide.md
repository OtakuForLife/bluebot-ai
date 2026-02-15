# Sprite Animation Guide

## Animation Fundamentals

### Frame Rate

**Common Frame Rates**:
- **60 FPS**: Smooth, modern, used for gameplay
- **30 FPS**: Standard for many animations
- **24 FPS**: Cinematic feel
- **12 FPS**: Classic animation, "on twos"
- **8-10 FPS**: Pixel art, retro games

**Choosing Frame Rate**:
- Higher FPS = smoother but more work
- Lower FPS = stylized, easier to produce
- Mix rates: gameplay at 60, animations at 12-24
- Pixel art often looks best at 8-12 FPS

### Timing and Spacing

**Timing**: How many frames an action takes
**Spacing**: Distance between frames

```
Slow movement: More frames, less spacing
Fast movement: Fewer frames, more spacing
Acceleration: Increasing spacing between frames
Deceleration: Decreasing spacing between frames
```

### Key Poses

1. **Key Frames**: Most important poses
2. **Breakdown Frames**: Major positions between keys
3. **In-betweens**: Frames that smooth the motion

**Workflow**:
1. Create key poses first
2. Add breakdowns
3. Fill in-betweens
4. Polish and refine

## Essential Animation Types

### Idle Animation

**Purpose**: Character at rest, waiting for input

**Guidelines**:
- Subtle movement (breathing, swaying)
- 1-2 second loop
- Seamless loop point
- Conveys personality
- Doesn't distract from gameplay

**Example Idle (8 frames)**:
```
Frame 1: Neutral pose
Frame 2-3: Slight rise (inhale)
Frame 4: Peak
Frame 5-6: Slight fall (exhale)
Frame 7-8: Return to neutral
```

### Walk Cycle

**Purpose**: Character moving at normal pace

**Key Poses** (8-frame walk):
```
Frame 1: Contact (foot touches ground)
Frame 2: Recoil (weight shifts)
Frame 3: Passing (legs pass each other)
Frame 4: High point (body at highest)
Frame 5: Contact (opposite foot)
Frame 6: Recoil (opposite side)
Frame 7: Passing (opposite)
Frame 8: High point (opposite)
```

**Tips**:
- Arms swing opposite to legs
- Body bobs up and down
- Head leads the motion
- Add secondary motion (hair, clothes)

### Run Cycle

**Purpose**: Character moving quickly

**Differences from Walk**:
- Fewer frames (4-6 frames)
- More exaggerated poses
- Both feet off ground at once
- Greater forward lean
- Faster arm swing

**Example Run (4 frames)**:
```
Frame 1: Push off (back leg extended)
Frame 2: Flight (both feet off ground)
Frame 3: Landing (front foot contacts)
Frame 4: Flight (opposite side)
```

### Jump Animation

**Purpose**: Character leaving and returning to ground

**Phases**:
1. **Anticipation** (1-2 frames): Crouch down
2. **Launch** (1 frame): Push off ground
3. **Ascent** (2-3 frames): Rising, arms up
4. **Peak** (1-2 frames): Apex of jump
5. **Descent** (2-3 frames): Falling, arms down
6. **Landing** (2-3 frames): Impact, crouch

**Tips**:
- Squash on anticipation and landing
- Stretch during ascent/descent
- Hold peak frame for control
- Add dust/particles on launch and landing

### Attack Animation

**Purpose**: Character performing offensive action

**Structure**:
1. **Windup** (2-4 frames): Anticipation
2. **Strike** (1-2 frames): Impact moment
3. **Follow-through** (2-3 frames): Recovery

**Tips**:
- Keep windup short for responsiveness
- Hold impact frame for emphasis
- Add motion blur or speed lines
- Include weapon trail effects
- Ensure clear hitbox timing

### Hit Reaction

**Purpose**: Character taking damage

**Types**:
- **Light Hit**: Small recoil (2-3 frames)
- **Heavy Hit**: Knockback (4-6 frames)
- **Stun**: Dazed state (looping)

**Tips**:
- Flash white or red on impact
- Squash on impact
- Stretch during knockback
- Add invincibility frames for gameplay

### Death Animation

**Purpose**: Character defeated

**Approaches**:
- **Dramatic**: Slow, exaggerated fall
- **Quick**: Fast disappear or poof
- **Ragdoll**: Physics-based (3D)

**Tips**:
- Make it satisfying but not too long
- Consider respawn time
- Add particle effects
- Fade out or remove from scene

## Pixel Art Animation

### Pixel Art Principles

**Pixel Placement**:
- Every pixel matters
- Avoid jagged lines (use anti-aliasing clusters)
- Maintain consistent pixel density
- Use dithering for gradients

**Color Limitations**:
- Limit palette (4-16 colors per sprite)
- Use hue shifting (shadows aren't just darker)
- Avoid pure black/white
- Create color ramps for shading

### Pixel Animation Techniques

**Sub-pixel Animation**:
- Move sprite position, not just pixels
- Allows smoother motion
- Good for camera movement
- Use with caution (can look blurry)

**Pixel-Perfect Movement**:
- Snap to pixel grid
- Crisp, retro feel
- Can feel choppy
- Good for authentic retro style

**Smear Frames**:
- Exaggerated in-between frames
- Creates motion blur effect
- Adds impact to fast movements
- Use sparingly

### Common Pixel Art Mistakes

❌ **Pillow Shading**: Shading in concentric circles
✅ **Directional Shading**: Light from consistent source

❌ **Too Many Colors**: Muddy, unclear sprites
✅ **Limited Palette**: Clear, readable sprites

❌ **Inconsistent Pixel Size**: Mixed resolutions
✅ **Consistent Scale**: Uniform pixel density

## Sprite Sheet Organization

### Layout Types

**Grid Layout**:
```
[Frame1][Frame2][Frame3][Frame4]
[Frame5][Frame6][Frame7][Frame8]
```
- Easy to parse programmatically
- Wastes space if frames vary in size
- Good for uniform animations

**Packed Layout**:
```
[Frame1][Frame2]
[Frame3][Frame4][Frame5]
```
- Efficient use of space
- Requires metadata (JSON, XML)
- Good for varied frame sizes

### Naming Conventions

```
character_idle_01.png
character_walk_01.png
character_walk_02.png
character_jump_01.png
character_attack_01.png
```

Or in sprite sheet:
```
character_spritesheet.png
character_spritesheet.json (metadata)
```

### Metadata Format (JSON)

```json
{
  "frames": {
    "idle_01": {
      "frame": {"x": 0, "y": 0, "w": 32, "h": 32},
      "duration": 100
    },
    "walk_01": {
      "frame": {"x": 32, "y": 0, "w": 32, "h": 32},
      "duration": 100
    }
  }
}
```

## Animation in Godot

### AnimatedSprite2D

```gdscript
# Setup in editor or code
@onready var sprite: AnimatedSprite2D = $AnimatedSprite2D

func _ready() -> void:
    sprite.play("idle")

func _process(delta: float) -> void:
    if Input.is_action_pressed("move_right"):
        sprite.play("walk")
        sprite.flip_h = false
    elif Input.is_action_pressed("move_left"):
        sprite.play("walk")
        sprite.flip_h = true
    else:
        sprite.play("idle")
```

### AnimationPlayer

```gdscript
# More control, can animate multiple properties
@onready var anim_player: AnimationPlayer = $AnimationPlayer

func attack() -> void:
    anim_player.play("attack")
    await anim_player.animation_finished
    # Attack complete, return to idle
```

## Performance Optimization

### Texture Atlasing

Combine multiple sprites into one texture:
- Reduces draw calls
- Faster rendering
- Smaller memory footprint
- Use tools like TexturePacker

### Frame Skipping

For background animations:
- Update every 2-3 frames instead of every frame
- Saves processing power
- Barely noticeable to players

### LOD (Level of Detail)

- Simpler animations for distant objects
- Fewer frames for background characters
- Disable animations off-screen

## Tools and Resources

**Software**:
- Aseprite: Pixel art and animation
- Piskel: Free browser-based pixel art
- Krita: Free, powerful 2D animation
- Spine: Professional 2D skeletal animation
- DragonBones: Free skeletal animation

**Resources**:
- Lospec: Palettes and tutorials
- OpenGameArt: Free sprites
- itch.io: Asset packs
- The Spriters Resource: Reference sprites

**Learning**:
- "Pixel Logic" by Michafrar
- "The Animator's Survival Kit" by Richard Williams
- GDC talks on animation
- YouTube: MortMort, Brandon James Greer

