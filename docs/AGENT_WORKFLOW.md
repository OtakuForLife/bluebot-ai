# Autonomous Game Studio

## Event-Driven Human + AI Collaborative Development Architecture

Version: 1.1

---

# 1. Purpose

This system is an autonomous game development environment where:

- AI agents perform development work.
- Human users can participate as team members.
- All participants are treated as actors.
- The system continuously discovers, creates, executes, and evaluates work.
- Development is driven by project goals rather than predefined task lists.

The architecture supports:

- Fully autonomous development
- Human-assisted development
- Human-only contributions
- Hybrid human/AI teams

without changing the underlying system.

A core feature of the system is the ability to switch between:

- **Automatic Task Pull Mode**
- **Manual Task Assignment Mode**

This allows users to decide how much control they want over task distribution.

---

# 2. Core Principles

## Principle 1 — Actors

Everything that performs work is an Actor.

Examples:

```text
Human User
Design Agent
Code Agent
QA Agent
Discovery Agent
Project Director
```

All actors interact through events.

Actors never communicate directly.

---

## Principle 2 — Shared State

The project state is the single source of truth.

Actors:

- Read state
    
- Analyze state
    
- Modify state through events
    

No actor owns the state.

---

## Principle 3 — Event-Driven Workflow

Nothing is executed directly.

Everything becomes an event.

Example:

```text
User requests inventory system
```

becomes

```text
FeatureRequested
```

The event is processed by the system.

---

## Principle 4 — Flexible Task Allocation

The system supports two task allocation modes.

### Automatic Task Pull Mode

Actors pull tasks from the marketplace automatically.

```text
Open Task
    ↓
Agent Claims Task
    ↓
Agent Executes Task
```

This mode maximizes autonomy.

---

### Manual Task Assignment Mode

The user assigns tasks to actors.

```text
Open Task
    ↓
User Assigns Task
    ↓
Assigned Actor Executes Task
```

This mode maximizes human control.

---

### Runtime Switching

The user may switch modes at any time through the UI.

The Project Director immediately applies the selected mode.

---

## Principle 5 — Continuous Discovery

The system continuously asks:

```text
What is missing?
What is wrong?
What can be improved?
```

Work emerges from analysis.

---

# 3. High-Level System Architecture

```text
User
  │

AI Actors

  │

Project Director

  │

Event Bus

  │

Shared State

  │

Task Marketplace

  │

Evaluation Layer

  │

Discovery Layer

  │

New Tasks
```

Development never stops until release criteria are reached.

---

# 4. Project Director

## Purpose

The Project Director is the governing component.

It controls project progression.

It does not perform implementation work.

---

## Responsibilities

### Project State Control

Tracks:

```text
Current Phase
Current Progress
Project Health
Release Status
```

---

### Workflow Supervision

Determines:

```text
Continue Development
Request Review
Run Audit
Generate Recovery Tasks
Enter Release Candidate
Mark Complete
```

---

### Task Allocation Governance

Tracks:

```text
Automatic Task Pull Mode
Manual Task Assignment Mode
```

Ensures actors follow the currently selected mode.

---

### Deadlock Detection

Detects:

```text
No Events
No Tasks
No State Changes
```

and initiates recovery.

---

### Release Governance

Determines:

```text
Project Complete?
Quality Targets Reached?
Release Candidate Ready?
```

---

# 5. Actor System

## Actor Definition

Every participant implements:

```python
class Actor:

    id: str

    actor_type: str

    capabilities: list

    subscriptions: list
```

---

## Actor Types

### Human Actor

Examples:

```text
Designer
Developer
Writer
Project Owner
```

Capabilities:

```text
Create Tasks
Claim Tasks
Assign Tasks
Review Work
Approve Changes
Change Vision
```

---

### AI Actor

Examples:

```text
Design Agent
Code Agent
QA Agent
Architecture Agent
```

Capabilities depend on specialization.

---

### System Actor

Examples:

```text
Project Director
Gap Analysis Agent
Discovery Agent
Evaluation Agent
```

These actors maintain project health.

---

# 6. Shared Project State

## Purpose

Represents the current project.

Every decision must be reproducible from state and events.

---

## Structure

```python
class ProjectState:

    project

    vision

    pillars

    goals

    tasks

    features

    assets

    code

    tests

    bugs

    metrics

    simulations

    architecture

    release_state

    task_allocation_mode
```

---

## Task Allocation Mode

Possible values:

```text
AUTO_PULL
MANUAL_ASSIGNMENT
```

This value is controlled through the UI and enforced by the Project Director.

---

## Rules

Actors:

```text
Read State
Generate Events
Update State Through Events
```

Never:

```text
Modify Another Actor
Call Another Actor Directly
```

---

# 7. Event System

## Purpose

Provides communication between actors.

---

## Event Structure

```python
class Event:

    id

    timestamp

    actor_id

    event_type

    payload
```

---

## Event Lifecycle

```text
Actor Action
      │
      ▼

Create Event

      │
      ▼

Event Bus

      │
      ▼

State Update

      │
      ▼

Subscribed Actors
```

---

## Task Allocation Events

```text
TaskAssigned
TaskUnassigned
TaskClaimed
TaskReleased
TaskAllocationModeChanged
```

---

# 8. Core Event Types

## Vision Events

```text
VisionCreated
VisionUpdated
GoalChanged
PillarAdded
```

---

## Feature Events

```text
FeatureRequested
FeatureDesigned
FeatureImplemented
FeatureCompleted
FeatureRejected
```

---

## Quality Events

```text
BugFound
BalanceIssue
PerformanceRegression
UXIssue
```

---

## Recovery Events

```text
DeadlockDetected
RecoveryStarted
RecoveryCompleted
```

---

## Review Events

```text
ReviewRequested
ReviewApproved
ReviewRejected
```

---

# 9. Task Marketplace

## Purpose

Stores available work.

---

## Task Structure

```python
class Task:

    id

    type

    priority

    status

    source

    dependencies

    owner

    assigned_actor
```

---

## Statuses

```text
Open
Assigned
Claimed
In Progress
Blocked
Review
Completed
Cancelled
```

---

## Ownership

Tasks may be owned by:

```text
Human Actors
AI Actors
```

Only one active owner is allowed.

---

## Allocation Modes

### Automatic Task Pull Mode

Actors automatically select suitable tasks.

Example:

```text
Open Task
    ↓
Code Agent Claims Task
    ↓
Implementation Starts
```

---

### Manual Task Assignment Mode

The user assigns tasks.

Example:

```text
Open Task
    ↓
User Assigns Task To QA Agent
    ↓
QA Agent Executes Task
```

---

# 10. Discovery Layer

## Purpose

Creates new work.

This is the primary source of tasks.

---

## Discovery Questions

The system continuously asks:

```text
What is missing?
What is incomplete?
What is broken?
What is inefficient?
What is untested?
What is unbalanced?
```

---

## Discovery Sources

### Vision Analysis

Detects:

```text
Missing Features
Missing Systems
Missing Content
```

---

### QA Analysis

Detects:

```text
Bugs
Missing Tests
Failures
```

---

### Simulation Analysis

Detects:

```text
Exploits
Balance Problems
Meta Issues
```

---

### Architecture Analysis

Detects:

```text
Technical Debt
Complexity
Coupling
```

---

# 11. Development Workflow

## Initial Phase

User provides:

```text
Game Idea
```

Example:

```text
Co-op Survival Game
```

---

## Vision Generation

Vision Agent creates:

```text
Vision
Pillars
Goals
Success Criteria
```

---

## Gap Analysis

System compares:

```text
Vision
vs
Current State
```

Outputs:

```text
Tasks
```

---

## Task Creation

Tasks enter marketplace.

---

## Task Allocation

The allocation process depends on the selected mode.

### Automatic Mode

```text
Task Created
      ↓
Agent Claims Task
      ↓
Execution
```

### Manual Mode

```text
Task Created
      ↓
User Assigns Task
      ↓
Execution
```

---

## Execution

Actor performs work.

Produces events.

Updates state.

---

## Evaluation

System evaluates:

```text
Quality
Progress
Completeness
```

---

## Discovery

System searches for:

```text
New Work
```

Loop repeats.

---

# 12. Human Participation

## Philosophy

Humans are actors.

Not administrators.

Not external observers.

---

## Human Contributions

Humans may:

```text
Claim Tasks
Assign Tasks
Create Features
Review Work
Write Content
Modify Designs
Provide Feedback
```

All actions become events.

---

## User Participation Modes

### Observer

User monitors progress.

### Team Member

User claims and completes tasks.

### Team Lead

User assigns tasks to AI actors and human actors.

### Creative Director

User reviews work and modifies project vision.

A single user may switch between these roles at any time.

---

## Example

User submits:

```text
Combat feels repetitive
```

Creates:

```text
UserFeedbackSubmitted
```

Discovery agents analyze feedback.

New tasks may be generated.

---

# 13. Review System

## Purpose

Validate completed work.

---

## Review Sources

```text
Human Review
AI Review
Automated Review
```

---

## Review Outcomes

```text
Approved
Changes Requested
Rejected
```

---

# 14. Deadlock Recovery

## Deadlock Conditions

```text
No Events
No State Changes
No Task Creation
No Task Completion
```

for a configurable duration.

---

## Recovery Process

### Step 1

Create:

```text
DeadlockDetected
```

---

### Step 2

Run Audit.

Audit:

```text
Tasks
Dependencies
Actors
State
Events
```

---

### Step 3

Generate Recovery Tasks.

Examples:

```text
Investigate Missing Feature
Resolve Dependency Loop
Restart Failed Actor
Run Vision Audit
```

---

# 15. Completion Logic

## Task Queue Empty

Run:

```text
Gap Analysis
```

---

## Gaps Found

Create Tasks.

Continue development.

---

## No Gaps Found

Run:

```text
Quality Audit
```

---

## Quality Below Target

Create optimization tasks.

---

## Quality Reached

Run:

```text
Polish Discovery
```

---

## No Additional Improvements

Enter:

```text
Release Candidate
```

---

## Release Candidate Approved

Project becomes:

```text
Completed
```

---

# 16. Finite State Machine

## Project States

```text
Initializing
Planning
Active
Review
Optimization
Release Candidate
Completed
Failed
```

---

## State Flow

```text
Initializing
      ↓

Planning
      ↓

Active
      ↓

Review
      ↓

Optimization
      ↓

Release Candidate
      ↓

Completed
```

Recovery may return any state back to:

```text
Active
```

---

# 17. Recommended Desktop Architecture

## UI

```text
PySide6
```

---

## Task Allocation Control

The UI must provide a global switch:

```text
[ Automatic Task Pull ]
[ Manual Task Assignment ]
```

Changing the switch generates:

```text
TaskAllocationModeChanged
```

event.

---

## Manual Assignment Interface

When Manual Assignment Mode is active:

```text
Open Tasks
      ↓
Select Task
      ↓
Select Actor
      ↓
Assign
```

Supported actors:

```text
Human User
Design Agent
Code Agent
QA Agent
Architecture Agent
```

---

## Workflow Engine

```text
LangGraph
```

---

## Persistence

```text
SQLite
```

Development phase:

```text
SQLite + SQLAlchemy
```

---

## Semantic Search

```text
pgvector
or
Local Vector Store
```

---

## Event Processing

```text
In-Process Event Dispatcher
```

No Kafka.

No RabbitMQ.

No Microservices.

---

## AI Layer

```text
OpenAI
Local Models
Hybrid Models
```

---

# 18. System Summary

The system functions as a self-organizing development studio.

Actors perform work.

Events coordinate communication.

State stores project knowledge.

Discovery continuously generates work.

Evaluation continuously measures quality.

The Project Director governs progression.

Humans and AI participate through the same actor model.

Task allocation can be fully autonomous through automatic task pulling or controlled by the user through manual task assignment.

The user may participate directly as a contributor while also assigning work to AI agents.

The project evolves from vision to release candidate through continuous analysis, execution, evaluation, and discovery loops.