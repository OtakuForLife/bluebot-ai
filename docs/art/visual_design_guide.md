# Visual Design Guide for Games

## Art Style Fundamentals

### Choosing an Art Style

Consider these factors when selecting an art style:

1. **Target Audience**: Who will play your game?
   - Children: Bright colors, simple shapes, friendly characters
   - Adults: More complex, potentially darker themes
   - Casual: Clean, accessible visuals
   - Hardcore: Detailed, immersive environments

2. **Technical Constraints**:
   - Team size and skill level
   - Development timeline
   - Target platforms (mobile needs simpler assets)
   - Performance requirements

3. **Genre Expectations**:
   - Platformers: Clear silhouettes, readable environments
   - RPGs: Detailed characters, rich environments
   - Puzzle games: Clean, minimalist design
   - Horror: Atmospheric lighting, unsettling aesthetics

### Common Art Styles

**Pixel Art**
- Pros: Nostalgic, fast to iterate, small file sizes
- Cons: Requires specific skills, can look dated if done poorly
- Best for: Retro games, indie projects, mobile games

**Low Poly 3D**
- Pros: Stylized, performant, distinctive look
- Cons: Can look generic, requires 3D skills
- Best for: Mobile 3D, stylized games, indie projects

**Hand-Painted/Stylized**
- Pros: Unique, artistic, timeless
- Cons: Time-consuming, requires strong art skills
- Best for: Story-driven games, artistic projects

**Realistic**
- Pros: Immersive, impressive visuals
- Cons: Very expensive, requires large team, ages poorly
- Best for: AAA games, simulation games

**Flat/Minimalist**
- Pros: Clean, modern, accessible
- Cons: Can lack personality, hard to differentiate
- Best for: Puzzle games, mobile games, UI-focused games

## Color Theory

### Color Palette Selection

**Monochromatic**: Variations of a single hue
- Creates harmony and cohesion
- Can feel monotonous if overused
- Good for minimalist games

**Analogous**: Colors next to each other on color wheel
- Harmonious and pleasing
- Creates smooth transitions
- Good for natural environments

**Complementary**: Opposite colors on color wheel
- High contrast and visual interest
- Can be jarring if not balanced
- Good for highlighting important elements

**Triadic**: Three evenly spaced colors
- Vibrant and balanced
- Offers variety while maintaining harmony
- Good for colorful, energetic games

### Color Psychology

- **Red**: Energy, danger, passion, urgency
- **Blue**: Calm, trust, sadness, cold
- **Green**: Nature, health, growth, safety
- **Yellow**: Happiness, caution, energy
- **Purple**: Mystery, magic, luxury
- **Orange**: Enthusiasm, creativity, warmth
- **Black**: Power, elegance, mystery, death
- **White**: Purity, simplicity, cleanliness

### Practical Color Usage

**UI Elements**:
- Health: Green or red (depending on context)
- Mana/Energy: Blue or cyan
- Danger/Warnings: Red or orange
- Success/Confirmation: Green
- Interactive elements: Bright, saturated colors
- Background: Desaturated, neutral colors

**Environment**:
- Use color to guide player attention
- Warm colors advance, cool colors recede
- Desaturate background elements
- Saturate important interactive objects

## Visual Hierarchy

### Principles

1. **Size**: Larger elements draw more attention
2. **Color**: Bright, saturated colors stand out
3. **Contrast**: High contrast creates focus
4. **Position**: Center and top-left get most attention
5. **Motion**: Moving elements attract the eye

### Application in Games

**Character Design**:
- Player character should be most visually distinct
- Use unique silhouette
- Brighter/more saturated than environment
- Clear visual center of interest

**Environment Design**:
- Path forward should be visually clear
- Important objects should stand out
- Background should recede
- Use lighting to guide attention

**UI Design**:
- Critical information should be largest/brightest
- Group related elements
- Use whitespace to separate sections
- Consistent visual language

## Readability and Clarity

### Silhouette Design

A good character/object should be recognizable by silhouette alone:

```
Test: Fill the character with solid black
- Can you still identify it?
- Can you tell what it's doing?
- Is it distinct from other characters?
```

**Tips**:
- Vary proportions (big head, small body, etc.)
- Add distinctive features (hat, weapon, tail)
- Use asymmetry for interest
- Avoid overlapping limbs in key poses

### Contrast and Separation

**Figure-Ground Separation**:
- Characters should contrast with background
- Use rim lighting or outlines
- Adjust background saturation/value
- Use depth of field effects

**Visual Noise Reduction**:
- Limit detail in less important areas
- Use solid colors for backgrounds
- Avoid busy textures behind gameplay
- Simplify distant objects

## Animation Principles

### 12 Principles of Animation (Applied to Games)

1. **Squash and Stretch**: Gives weight and flexibility
2. **Anticipation**: Prepares player for action
3. **Staging**: Direct attention to important action
4. **Straight Ahead vs Pose-to-Pose**: Different animation approaches
5. **Follow Through**: Parts continue moving after main action stops
6. **Slow In/Slow Out**: Ease in and out of movements
7. **Arcs**: Natural movement follows curved paths
8. **Secondary Action**: Supporting actions add life
9. **Timing**: Speed conveys weight and emotion
10. **Exaggeration**: Push beyond reality for impact
11. **Solid Drawing**: Maintain volume and weight
12. **Appeal**: Make characters engaging and interesting

### Game-Specific Animation

**Responsive Animation**:
- Keep startup frames minimal (< 5 frames)
- Provide clear visual feedback
- Allow animation canceling for responsiveness
- Use blend trees for smooth transitions

**Idle Animations**:
- Subtle breathing or swaying
- Occasional special idles for personality
- Loop seamlessly
- Don't distract from gameplay

**Impact Frames**:
- Freeze frame on hit for emphasis
- Screen shake for powerful attacks
- Particle effects for visual punch
- Sound effects synchronized with visuals

## Asset Creation Guidelines

### Sprite/Texture Resolution

**Pixel Art**:
- Common sizes: 16x16, 32x32, 64x64
- Keep consistent pixel density
- Avoid sub-pixel positioning
- Use nearest-neighbor filtering

**HD 2D**:
- Base resolution: 1920x1080 or higher
- Create at 2x-4x final size for downscaling
- Use power-of-2 dimensions for optimization
- Consider texture atlasing

**3D Textures**:
- Use power-of-2 dimensions (512, 1024, 2048)
- PBR workflow: Albedo, Normal, Roughness, Metallic
- Optimize for target platform
- Use texture compression

### File Formats

**2D Assets**:
- PNG: Lossless, supports transparency (UI, sprites)
- JPG: Lossy, smaller file size (backgrounds, photos)
- SVG: Vector, scalable (logos, simple graphics)

**3D Assets**:
- FBX/GLTF: 3D models and animations
- OBJ: Simple static meshes
- Blend: Godot can import Blender files directly

### Optimization

**Texture Optimization**:
- Use texture atlases to reduce draw calls
- Compress textures appropriately
- Use mipmaps for 3D textures
- Remove unused alpha channels

**Polygon Count**:
- Mobile: 5k-10k triangles per character
- PC/Console: 20k-50k triangles per character
- Use LOD (Level of Detail) for distant objects
- Optimize topology for deformation

## Lighting and Atmosphere

### Lighting Basics

**Three-Point Lighting**:
1. **Key Light**: Main light source, creates primary shadows
2. **Fill Light**: Softens shadows, adds detail
3. **Rim Light**: Separates subject from background

**Mood Through Lighting**:
- Bright, even lighting: Happy, safe, clear
- Dark, high contrast: Dramatic, dangerous, mysterious
- Warm colors: Comfortable, inviting, energetic
- Cool colors: Calm, sad, eerie

### Time of Day

**Day**: Bright, high contrast, clear visibility
**Sunset/Sunrise**: Warm, long shadows, dramatic
**Night**: Dark, limited visibility, mysterious
**Overcast**: Soft shadows, muted colors, melancholic

## UI/UX Visual Design

### Consistency

- Use consistent color scheme
- Maintain visual hierarchy
- Standardize button styles
- Keep spacing uniform

### Feedback

- Hover states for interactive elements
- Click/press animations
- Progress indicators
- Success/error states

### Accessibility

- Sufficient contrast (WCAG AA: 4.5:1 for text)
- Colorblind-friendly palettes
- Scalable UI elements
- Clear iconography

## Resources

- *The Art of Game Design* by Jesse Schell
- *Color and Light* by James Gurney
- *The Animator's Survival Kit* by Richard Williams
- Lospec (pixel art palettes and tutorials)
- Game Art Tricks (online resource)

