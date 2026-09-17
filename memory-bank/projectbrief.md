# Project Brief

## What this is

Bluebot AI is a **local desktop application** that uses multiple autonomous agents to help design, implement, and manage **Godot** game projects.

It runs on the user's machine, talks to a local (or optional remote) LLM, and treats the Godot project as a file tree that agents read and write through controlled tools.

## Goal

Automate and accelerate common game-development workflows — vision, design docs, GDScript, art direction, task management — while remaining:

- **offline-first** (Ollama by default; no cloud required)
- **100% open source** (OSI-licensed stack)
- **human-in-the-loop** (humans are actors, not just observers)

## In scope

- Orchestrate specialized agents (discovery, design, programming, art, project direction).
- Generate and modify Godot-compatible files (GDScript, scenes, design docs, assets).
- Agile task marketplace: create, claim, review, complete tasks.
- Cross-platform desktop UI (Windows and Linux; PySide6).
- Event-driven backend so UI, agents, and project state stay loosely coupled.

## Out of scope (now)

- Requiring cloud/paid APIs to function.
- Proprietary engines or middleware.
- Shipping a bundled Godot install (user provides Godot).
- Microservices, Kafka, or any distributed event bus.

## Users

Game developers who have Godot installed and want an AI studio sitting beside the engine — not a replacement for it.

## Success looks like

A user can create or open a project, start the agentic system, watch agents discover gaps, file tasks, implement work, and pause for human review — all without leaving the desktop app or sending project files to a cloud.
