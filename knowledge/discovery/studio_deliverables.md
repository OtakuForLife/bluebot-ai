# Studio Deliverables Catalog

Discovery uses this catalog to map **capabilities** (what the project still needs) to concrete **artifacts** (files to produce), **rubrics** (quality specs in `knowledge/`), and **task types** (marketplace routing to specialists).

## How to use this catalog

1. **Inspect content, not just paths.** A file may exist but be empty, a stub, or missing required sections. Read files before deciding a capability is satisfied.
2. **Pick the highest-priority row** whose capability is still missing or inadequate.
3. **Call `read_rubric`** with the rubric id to derive objective acceptance criteria.
4. **Call `create_task`** with the matching `task_type`, `capability`, `recommended_artifact`, and `rubric`.
5. **Match `task_description` to the gap type:**
   - File missing/empty → start with **"Create {artifact}: ..."**
   - File exists but inadequate → start with **"Improve {artifact}: ..."** and list specific deficiencies from `read_file` (never say "Create" for an existing file).

## Priority order

Work through gaps in priority order (1 = first). Skip a row when:

- An **active** task (todo/in_progress/review) already targets it, OR
- `read_file` shows the artifact exists with adequate rubric content.

Do **not** skip a row only because a **done** task exists — approved work can still be
incomplete or fail the rubric. Create an improvement task on the same artifact when content
is inadequate.

| priority | capability | recommended_artifact | rubric | task_type |
|----------|------------|----------------------|--------|-----------|
| 1 | game_vision | design/VISION.md | vision_document_guide | design |
| 2 | core_mechanics | design/MECHANICS.md | mechanics_design | design |
| 3 | player_experience | design/UX.md | ux_design_principles | design |
| 4 | visual_direction | design/GRAPHICS.md | visual_design_guide | art |
| 5 | first_playable | godot/main.gd | godot_best_practices | gameplay |

## Capability definitions

### game_vision
The project lacks a complete game vision: genre, hook, target audience, core loop, and success criteria aligned with the game brief.

### core_mechanics
Vision exists but core mechanics (rules, systems, player verbs) are undefined or only mentioned at a high level.

### player_experience
Mechanics exist but UX flow, onboarding, feedback, and accessibility are not documented.

### visual_direction
Design docs exist but art style, palette, and asset direction are not specified.

### first_playable
Design foundation is sufficient but no playable Godot implementation exists yet.

## Rubric ids

Rubrics are markdown guides under `knowledge/`. Valid ids:

- `vision_document_guide` → game design vision spec
- `mechanics_design` → mechanics document spec
- `ux_design_principles` → UX document spec
- `visual_design_guide` → art direction spec
- `godot_best_practices` → Godot implementation spec

## When no gaps remain

If every catalog row is satisfied (content meets rubric) and no active tasks remain, call `create_task` with `no_more_tasks=true`, then `finish`.
