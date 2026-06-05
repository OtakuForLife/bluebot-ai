"""Rubric id → knowledge file resolution for Discovery and read_rubric tool."""

from pathlib import Path

_KNOWLEDGE_ROOT = Path(__file__).parent.parent.parent / "knowledge"

# rubric_id → path relative to knowledge/
RUBRIC_PATHS: dict[str, str] = {
    "vision_document_guide": "game_design/vision_document_guide.md",
    "mechanics_design": "game_design/mechanics_design.md",
    "ux_design_principles": "game_design/ux_design_principles.md",
    "visual_design_guide": "art/visual_design_guide.md",
    "godot_best_practices": "programming/godot_best_practices.md",
    "sprite_animation_guide": "art/sprite_animation_guide.md",
    "testing_guide": "qa/testing_guide.md",
    "sound_design_guide": "audio/sound_design_guide.md",
}


def list_rubric_ids() -> list[str]:
    """Return all known rubric ids."""
    return sorted(RUBRIC_PATHS.keys())


def load_rubric(rubric_id: str) -> str | None:
    """Load rubric markdown by id. Returns None if unknown or unreadable."""
    rel = RUBRIC_PATHS.get(rubric_id.strip())
    if not rel:
        return None
    path = _KNOWLEDGE_ROOT / rel
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None
