"""Prompt templates for different agent roles.

This module provides specialized prompt templates for each agent type,
incorporating knowledge base content and task-specific instructions.
"""

from typing import Optional


class PromptTemplate:
    """Base class for prompt templates."""

    @staticmethod
    def format_knowledge_context(knowledge_docs: list[tuple[str, str]], max_docs: int = 5) -> str:
        """Format knowledge base documents into context.

        Args:
            knowledge_docs: List of (key, content) tuples from knowledge base search.
            max_docs: Maximum number of documents to include.

        Returns:
            Formatted knowledge context string.
        """
        if not knowledge_docs:
            return "No relevant documentation found."

        context_parts = ["# Relevant Documentation\n"]
        for i, (key, content) in enumerate(knowledge_docs[:max_docs]):
            context_parts.append(f"\n## Document: {key}\n")
            # Truncate very long documents
            if len(content) > 2000:
                content = content[:2000] + "\n...(truncated)"
            context_parts.append(content)

        return "\n".join(context_parts)


class GameProgrammerPrompts(PromptTemplate):
    """Prompt templates for the Game Programmer agent."""

    SYSTEM_PROMPT = """You are an expert game programmer specializing in Godot Engine and GDScript.
Your role is to write clean, efficient, and well-documented game code.

Key responsibilities:
- Implement gameplay systems and mechanics
- Write physics and collision code
- Develop AI behaviors
- Create reusable, modular scripts
- Follow Godot best practices

Always provide complete, working code with comments explaining key sections."""

    @staticmethod
    def create_script_prompt(script_name: str, description: str, knowledge_context: str) -> str:
        """Create a prompt for generating a GDScript file.

        Args:
            script_name: Name of the script to create.
            description: Description of what the script should do.
            knowledge_context: Relevant Godot documentation.

        Returns:
            Formatted prompt string.
        """
        return f"""{knowledge_context}

# Task: Create GDScript File

Create a GDScript file named `{script_name}` with the following requirements:

{description}

Requirements:
- Use proper GDScript syntax and conventions
- Include class_name declaration if appropriate
- Add docstring comments explaining the script's purpose
- Implement all necessary functions with proper type hints
- Follow Godot best practices from the documentation above
- Include example usage in comments if helpful

Provide the complete script code."""

    @staticmethod
    def implement_gameplay_prompt(feature: str, knowledge_context: str) -> str:
        """Create a prompt for implementing a gameplay feature.

        Args:
            feature: Description of the gameplay feature.
            knowledge_context: Relevant Godot documentation.

        Returns:
            Formatted prompt string.
        """
        return f"""{knowledge_context}

# Task: Implement Gameplay Feature

Implement the following gameplay feature:

{feature}

Provide:
1. Complete GDScript code for the feature
2. Explanation of how it works
3. Any scene setup requirements (nodes, signals, etc.)
4. Usage examples

Ensure the code is production-ready and follows Godot best practices."""


class GameDesignerPrompts(PromptTemplate):
    """Prompt templates for the Game Designer agent."""

    SYSTEM_PROMPT = """You are an expert game designer with deep knowledge of game mechanics, player psychology, and UX design.
Your role is to create engaging, balanced, and fun game experiences.

Key responsibilities:
- Define game mechanics and rules
- Design player progression systems
- Create compelling narratives and storyboards
- Ensure good user experience (UX)
- Balance gameplay for fairness and fun

Always provide detailed, actionable design documents."""

    @staticmethod
    def create_vision_prompt(
        project_name: str,
        project_description: str,
        genres: list[str],
        elements: list[str],
        knowledge_context: str
    ) -> str:
        """Create a prompt for generating a game vision document.

        Args:
            project_name: Name of the game project.
            project_description: Description of the game.
            genres: List of game genres.
            elements: List of game elements.
            knowledge_context: Relevant game design documentation.

        Returns:
            Formatted prompt string.
        """
        genres_str = ', '.join(genres) if genres else 'Not specified'
        elements_str = ', '.join(elements) if elements else 'Not specified'

        return f"""# Task: Create Game Vision Document

You are creating a comprehensive vision document for a new game project.

## Project Information
- **Name**: {project_name}
- **Description**: {project_description}
- **Genres**: {genres_str}
- **Game Elements**: {elements_str}

{knowledge_context}

## Your Task
Create a detailed game vision document that includes:

1. **Executive Summary** (2-3 paragraphs)
   - Core concept and hook
   - What makes this game unique
   - Target audience

2. **Game Overview**
   - Genre and style
   - Platform and technical scope
   - Core gameplay loop (in 3-5 sentences)

3. **Vision Statement**
   - What experience should players have?
   - What emotions should the game evoke?
   - What should players remember after playing?

4. **Unique Selling Points (USPs)**
   - List 3-5 features that make this game stand out
   - Why would players choose this over similar games?

5. **Target Audience**
   - Primary demographic
   - Player motivations and preferences
   - Accessibility considerations

6. **Scope and Constraints**
   - Estimated development timeline (rough phases)
   - Technical requirements
   - Resource considerations

7. **Success Criteria**
   - What does "done" look like?
   - Key features that must be included
   - Quality benchmarks

Use the best practices from the knowledge base above to create a professional, well-structured vision document.
Format the document in clear, well-structured Markdown. Be specific and actionable.
The vision should inspire the development team while being realistic and achievable."""

    @staticmethod
    def define_mechanics_prompt(mechanic_type: str, description: str, knowledge_context: str) -> str:
        """Create a prompt for defining game mechanics.

        Args:
            mechanic_type: Type of mechanic (combat, movement, etc.).
            description: Description of the desired mechanic.
            knowledge_context: Relevant game design documentation.

        Returns:
            Formatted prompt string.
        """
        return f"""{knowledge_context}

# Task: Define Game Mechanic

Define the following game mechanic:

Type: {mechanic_type}
Description: {description}

Provide a comprehensive design document including:
1. Core mechanic description
2. Rules and constraints
3. Player interactions
4. Balance considerations
5. Implementation notes for programmers
6. Example scenarios

Format as a structured design document."""


class GameArtistPrompts(PromptTemplate):
    """Prompt templates for the Game Artist agent."""

    SYSTEM_PROMPT = """You are an expert game artist specializing in 2D/3D art, animation, and UI design.
Your role is to create visually appealing and functional game assets.

Key responsibilities:
- Design 2D sprites and 3D models
- Create animations and visual effects
- Design user interfaces
- Manage textures and materials
- Ensure visual consistency

Always provide detailed asset specifications and design guidelines."""

    @staticmethod
    def create_asset_prompt(asset_type: str, description: str, knowledge_context: str) -> str:
        """Create a prompt for designing a game asset.

        Args:
            asset_type: Type of asset (sprite, model, UI, etc.).
            description: Description of the desired asset.
            knowledge_context: Relevant art documentation.

        Returns:
            Formatted prompt string.
        """
        return f"""{knowledge_context}

# Task: Design Game Asset

Create specifications for the following asset:

Type: {asset_type}
Description: {description}

Provide:
1. Detailed visual description
2. Dimensions and technical specifications
3. Color palette and style guide
4. Animation requirements (if applicable)
5. File format and export settings for Godot
6. Implementation notes

Format as a detailed asset specification document."""


class QATesterPrompts(PromptTemplate):
    """Prompt templates for the QA Tester agent."""

    SYSTEM_PROMPT = """You are an expert QA tester specializing in game testing and quality assurance.
Your role is to identify bugs, ensure game stability, and verify game balance.

Key responsibilities:
- Design comprehensive test plans
- Identify and document bugs
- Verify bug fixes
- Test game balance and difficulty
- Ensure performance and stability

Always provide detailed, actionable bug reports and test plans."""

    @staticmethod
    def create_test_plan_prompt(feature: str, knowledge_context: str) -> str:
        """Create a prompt for generating a test plan.

        Args:
            feature: Feature to test.
            knowledge_context: Relevant QA documentation.

        Returns:
            Formatted prompt string.
        """
        return f"""{knowledge_context}

# Task: Create Test Plan

Create a comprehensive test plan for:

{feature}

Provide:
1. Test objectives
2. Test cases (with steps and expected results)
3. Edge cases to verify
4. Performance benchmarks
5. Acceptance criteria

Format as a structured test plan document."""
