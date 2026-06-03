
# UI Workflow

## New Project Workflow

```
main.py
  ↓
ProjectSelectionWindow
  ↓
Create Project Button
  ↓
[Create Project Command]
  ↓
Project Structure created
  ↓
Orchestrator.create_state()
  ↓
MainWindow
```
## Load Existing Project

```
main.py
  ↓
ProjectSelectionWindow (select existing)
  ↓
Orchestrator.load_state()
  ↓
MainWindow
```
## Start Agentic System

```
MainWindow
  ↓
Start Orchestrator Button
  ↓
[Start Orchestrator Command]
  ↓
Agent Workflow starts with loaded state
```

## Manual Task Creation

```
Main Window → Stop Orchestrator Button → Agents finish working on current task
  ↓
New Task Button
  ↓
QtCommandBridge.dispatch(CreateTaskCommand)
  ↓
New Task is created and visible for Project Manager Agent
```
