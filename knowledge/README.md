# Bluebot AI Agent Documentation

This directory contains documentation that agents use to inform their work. Each agent has access to relevant documentation in their knowledge base.

## Directory Structure

```
docs/
├── game_design/          # Game Designer Agent documentation
│   ├── vision_document_guide.md
│   ├── mechanics_design.md
│   └── ux_design_principles.md
├── programming/          # Game Programmer Agent documentation
│   ├── godot_best_practices.md
│   └── code_architecture.md
├── art/                  # Game Artist Agent documentation
│   ├── visual_design_guide.md
│   └── sprite_animation_guide.md
├── audio/                # Audio Engineer Agent documentation
│   └── sound_design_guide.md
├── qa/                   # QA Tester Agent documentation
│   └── testing_guide.md
└── production/           # Game Producer Agent documentation
    └── project_management.md
```

## Agent Documentation Mapping

### Game Designer Agent
**Knowledge Base**: `docs/game_design/`
- Vision document creation guidelines
- Game mechanics design patterns
- UX/UI design principles
- Player psychology and engagement

### Game Programmer Agent
**Knowledge Base**: `docs/programming/`
- Godot Engine best practices
- GDScript coding standards
- Code architecture patterns
- Performance optimization techniques

### Game Artist Agent
**Knowledge Base**: `docs/art/`
- Visual design principles
- Color theory and composition
- Sprite and animation guidelines
- Art style consistency

### Audio Engineer Agent
**Knowledge Base**: `docs/audio/`
- Sound design fundamentals
- Music composition for games
- Audio implementation in Godot
- Mixing and mastering techniques

### QA Tester Agent
**Knowledge Base**: `docs/qa/`
- Testing methodologies
- Bug reporting standards
- Test case creation
- Quality assurance processes

### Game Producer Agent
**Knowledge Base**: `docs/production/`
- Project management frameworks
- Agile/Scrum for game development
- Risk management
- Team coordination strategies

## How Agents Use Documentation

1. **Knowledge Base Loading**: Each agent loads relevant documentation on initialization
2. **Context Retrieval**: Agents search their knowledge base when working on tasks
3. **LLM Integration**: Documentation context is provided to LLM for informed decision-making
4. **Best Practices**: Agents follow guidelines from documentation in their outputs

## Adding New Documentation

To add new documentation:

1. Create a markdown file in the appropriate subdirectory
2. Use clear headings and structure
3. Include practical examples
4. Reference industry standards
5. Keep content focused and actionable

## Documentation Standards

- **Format**: Markdown (.md)
- **Structure**: Clear headings, bullet points, code examples
- **Length**: Comprehensive but concise (aim for < 200 lines per file)
- **Examples**: Include practical, game-specific examples
- **References**: Link to external resources when helpful

## Updating Documentation

Documentation should be updated when:
- New best practices emerge
- Godot Engine updates introduce new features
- Team discovers better approaches
- Industry standards change

## Resources

All documentation is based on industry best practices, official Godot documentation, and established game development principles.

