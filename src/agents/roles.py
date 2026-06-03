from enum import Enum


class AgentRole(Enum):
    """Enumeration of possible agent roles."""
    GAME_DESIGNER = "game_designer"
    GAME_PROGRAMMER = "game_programmer"
    GAME_ARTIST = "game_artist"
    GAME_PRODUCER = "game_producer"
    QA_TESTER = "qa_tester"
    AUDIO_ENGINEER = "audio_engineer"
    PROJECT_DIRECTOR = "project_director"
    DISCOVERY = "discovery"