# Game Sound Design Guide

## Sound Design Fundamentals

### Purpose of Game Audio

1. **Feedback**: Confirm player actions
2. **Atmosphere**: Create mood and immersion
3. **Information**: Communicate game state
4. **Emotion**: Enhance emotional impact
5. **Guidance**: Direct player attention

### Audio Categories

**Sound Effects (SFX)**:
- UI sounds (clicks, notifications)
- Character sounds (footsteps, voice)
- Weapon/combat sounds
- Environmental sounds (wind, water)
- Impact sounds (collisions, explosions)

**Music**:
- Main theme
- Level/area music
- Combat music
- Menu music
- Ambient soundscapes

**Voice**:
- Dialogue
- Narration
- Character reactions
- Tutorial instructions

## Sound Effect Design

### Layering

Build complex sounds from simple elements:

**Example: Sword Swing**
```
Layer 1: Whoosh (air movement)
Layer 2: Metal scrape (blade sound)
Layer 3: Cloth rustle (character movement)
Result: Rich, believable sword swing
```

**Example: Explosion**
```
Layer 1: Low boom (bass impact)
Layer 2: Crackle/debris (mid-range detail)
Layer 3: High sizzle (high-frequency detail)
Layer 4: Reverb tail (environment)
Result: Full, impactful explosion
```

### Variation

Avoid repetition fatigue:

**Techniques**:
- Create 3-5 variations of common sounds
- Randomize pitch (±5-10%)
- Randomize volume (±3-6 dB)
- Randomize playback position
- Use round-robin playback

**Example in Godot**:
```gdscript
var footstep_sounds: Array[AudioStream] = [
    preload("res://audio/footstep_01.wav"),
    preload("res://audio/footstep_02.wav"),
    preload("res://audio/footstep_03.wav"),
]

func play_footstep() -> void:
    var sound = footstep_sounds.pick_random()
    audio_player.stream = sound
    audio_player.pitch_scale = randf_range(0.95, 1.05)
    audio_player.play()
```

### Frequency Spectrum

Balance sounds across frequency ranges:

**Low (20-250 Hz)**:
- Bass, rumble, power
- Explosions, engines, thunder
- Too much = muddy mix

**Mid (250-4000 Hz)**:
- Most important for clarity
- Dialogue, instruments, impacts
- Where human hearing is most sensitive

**High (4000-20000 Hz)**:
- Brightness, air, detail
- Sizzle, sparkle, metal
- Too much = harsh, fatiguing

### Dynamic Range

**Compression**: Reduce dynamic range
- Makes quiet sounds louder
- Makes loud sounds quieter
- Increases perceived loudness
- Use on dialogue, music

**Limiting**: Prevent clipping
- Hard ceiling on volume
- Prevents distortion
- Use on master output

## Music Design

### Adaptive Music

Music that responds to gameplay:

**Horizontal Re-sequencing**:
- Switch between different sections
- Example: Calm exploration → Intense combat
- Seamless transitions at measure boundaries

**Vertical Remixing**:
- Layer tracks on/off
- Example: Add drums when enemies appear
- All layers play in sync

**Generative Music**:
- Procedurally generated
- Never repeats exactly
- Good for ambient, exploration

### Music Loops

**Creating Seamless Loops**:
1. Match tempo and key
2. Align waveforms at loop points
3. Use crossfades if needed
4. Test loop multiple times
5. Ensure no clicks or pops

**Loop Length**:
- Short loops (30-60s): Can feel repetitive
- Medium loops (1-2 min): Good balance
- Long loops (3-5 min): More variety, larger files

### Music Mixing

**Levels**:
- Music: -20 to -15 dB (background)
- SFX: -10 to -5 dB (foreground)
- Dialogue: -6 to -3 dB (priority)

**Ducking**:
- Lower music volume during dialogue/SFX
- Automatic with sidechain compression
- Improves clarity

## Implementation in Godot

### Audio Buses

```
Master
├── Music
│   ├── Exploration
│   └── Combat
├── SFX
│   ├── UI
│   ├── Player
│   └── Environment
└── Voice
```

**Setup**:
1. Create buses in Audio panel
2. Add effects (reverb, compression)
3. Route AudioStreamPlayers to appropriate buses

### AudioStreamPlayer Types

**AudioStreamPlayer**: 2D positional audio
**AudioStreamPlayer2D**: 2D positional audio
**AudioStreamPlayer3D**: 3D positional audio

```gdscript
# 2D positional audio
@onready var audio: AudioStreamPlayer2D = $AudioStreamPlayer2D

func _ready() -> void:
    audio.stream = preload("res://audio/ambient.ogg")
    audio.play()
```

### Audio Zones

Create areas with different audio:

```gdscript
# AudioZone.gd
extends Area2D

@export var ambient_sound: AudioStream
@export var reverb_amount: float = 0.5

func _on_body_entered(body: Node2D) -> void:
    if body.is_in_group("player"):
        AudioManager.set_ambient(ambient_sound)
        AudioManager.set_reverb(reverb_amount)
```

### Music Transitions

```gdscript
# MusicManager.gd (Autoload)
extends Node

var current_music: AudioStreamPlayer
var next_music: AudioStreamPlayer
var fade_duration: float = 2.0

func transition_to(music_stream: AudioStream) -> void:
    if next_music:
        next_music.queue_free()
    
    next_music = AudioStreamPlayer.new()
    next_music.stream = music_stream
    next_music.bus = "Music"
    next_music.volume_db = -80
    add_child(next_music)
    next_music.play()
    
    # Fade out current, fade in next
    var tween = create_tween()
    if current_music:
        tween.tween_property(current_music, "volume_db", -80, fade_duration)
    tween.parallel().tween_property(next_music, "volume_db", 0, fade_duration)
    tween.tween_callback(_on_transition_complete)

func _on_transition_complete() -> void:
    if current_music:
        current_music.queue_free()
    current_music = next_music
    next_music = null
```

## Audio File Formats

### Format Comparison

**WAV**:
- Uncompressed, lossless
- Large file size
- Best quality
- Use for: Short SFX, source files

**OGG Vorbis**:
- Compressed, lossy
- Good quality, small size
- Loops seamlessly
- Use for: Music, ambient sounds

**MP3**:
- Compressed, lossy
- Widely supported
- Licensing issues
- Use for: Generally avoid in games

### Godot Recommendations

- **SFX**: WAV (< 1 second) or OGG (> 1 second)
- **Music**: OGG Vorbis
- **Voice**: OGG Vorbis
- **Sample Rate**: 44.1 kHz or 48 kHz
- **Bit Depth**: 16-bit (sufficient for games)

## Mixing and Mastering

### Mixing Principles

1. **Balance**: All elements audible
2. **Clarity**: No frequency masking
3. **Space**: Use panning and reverb
4. **Dynamics**: Appropriate loudness
5. **Cohesion**: Everything fits together

### EQ (Equalization)

**Common EQ Moves**:
- **Footsteps**: Boost 2-4 kHz for presence
- **Explosions**: Boost 60-100 Hz for power
- **Dialogue**: Cut below 80 Hz, boost 2-5 kHz
- **Music**: Gentle cuts/boosts, avoid extremes

### Reverb

Adds space and depth:

**Types**:
- **Room**: Small, intimate spaces
- **Hall**: Large, open spaces
- **Plate**: Smooth, musical reverb
- **Spring**: Vintage, metallic sound

**Parameters**:
- **Decay Time**: How long reverb lasts
- **Pre-delay**: Gap before reverb starts
- **Wet/Dry**: Mix of effect vs original

**Usage**:
- Indoor scenes: Short decay (0.5-1.5s)
- Outdoor scenes: Minimal reverb
- Caves/halls: Long decay (2-4s)

## Accessibility

### Volume Controls

Provide separate sliders for:
- Master volume
- Music volume
- SFX volume
- Voice volume

### Subtitles

- Display all dialogue
- Include speaker names
- Describe important sounds
- Sync with audio timing

### Visual Indicators

For hearing-impaired players:
- Visual cues for off-screen sounds
- Directional indicators
- Subtitle for ambient sounds

## Performance Optimization

### Audio Streaming

- Stream long audio files (music)
- Load short sounds into memory (SFX)
- Reduces memory usage
- Slight CPU overhead

### Audio Pooling

Reuse AudioStreamPlayer nodes:

```gdscript
var audio_pool: Array[AudioStreamPlayer] = []

func get_audio_player() -> AudioStreamPlayer:
    for player in audio_pool:
        if not player.playing:
            return player
    
    # Pool exhausted, create new
    var player = AudioStreamPlayer.new()
    add_child(player)
    audio_pool.append(player)
    return player
```

### Limit Simultaneous Sounds

```gdscript
const MAX_SOUNDS = 32

func play_sound(sound: AudioStream) -> void:
    if get_playing_count() >= MAX_SOUNDS:
        return  # Skip this sound
    
    var player = get_audio_player()
    player.stream = sound
    player.play()
```

## Resources

**Software**:
- Audacity: Free audio editor
- Reaper: Affordable DAW
- FMOD/Wwise: Professional game audio middleware
- Bfxr/Sfxr: Retro sound effect generators

**Sound Libraries**:
- Freesound.org: Free sound effects
- OpenGameArt: Free game audio
- Incompetech: Free music (Kevin MacLeod)
- Purple Planet: Free music

**Learning**:
- *The Game Audio Tutorial* by Stevens & Raybould
- GDC Audio talks
- A Sound Effect blog
- Game Audio Institute

