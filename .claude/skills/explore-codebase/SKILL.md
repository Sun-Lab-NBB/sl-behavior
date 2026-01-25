---
name: exploring-codebase
description: >-
  Performs in-depth codebase exploration at the start of a coding session. Builds comprehensive
  understanding of project structure, architecture, key components, and patterns. Use when starting
  a new session, when asked to understand or explore the codebase, when asked "what does this project
  do", when exploring unfamiliar code, or when the user asks about project structure or architecture.
---

# Codebase Exploration

Performs thorough codebase exploration to build deep understanding before coding work begins.

---

## Exploration Approach

Use the Task tool with `subagent_type: Explore` to investigate the codebase. Focus on understanding:

1. **Project purpose and structure** - README, documentation, directory layout
2. **Architecture** - Main components, how they interact, data flow patterns
3. **Core code** - Key classes, data models, processing functions
4. **Configuration** - How the project is configured and customized
5. **Dependencies** - External libraries and integrations
6. **Patterns and conventions** - Coding style, naming conventions, design patterns

Adapt exploration depth based on project size and complexity. For small projects, a quick overview
suffices. For large projects, explore systematically.

---

## Guiding Questions

Answer these questions during exploration:

### Architecture
- What is the main entry point or controller?
- How does data flow through the processing pipeline?
- What external systems does this integrate with?

### Patterns
- What naming conventions are used?
- What design patterns appear (enums, dataclasses, parallel processing)?
- How is configuration managed?

### Structure
- Where is the core business logic?
- Where are tests located?
- What build/tooling configuration exists?

---

## Output Format

Provide a structured summary including:

- Project purpose (1-2 sentences)
- Key components table
- Important files list with paths
- Notable patterns or conventions
- Any areas of complexity or concern

### Example Output

```markdown
## Project Purpose

Processes non-visual behavior data from Mesoscope-VR experiments. Extracts data from `.npz` log
archives and saves as `.feather` files for downstream integration via sl-forgery.

## Key Components

| Component              | Location                          | Purpose                                          |
|------------------------|-----------------------------------|--------------------------------------------------|
| Processing Pipeline    | src/sl_behavior/pipeline.py       | Job orchestration and execution management       |
| Runtime Processor      | src/sl_behavior/runtime.py        | VR system state and trial sequence extraction    |
| Microcontroller Parser | src/sl_behavior/microcontrollers.py | Hardware module data extraction and parsing    |
| Camera Processor       | src/sl_behavior/camera.py         | Frame timestamp extraction                       |
| CLI Interface          | src/sl_behavior/cli.py            | Command-line entry point                         |

## Important Files

- `src/sl_behavior/pipeline.py` - Central processing orchestration with BehaviorJobNames enum
- `src/sl_behavior/runtime.py` - VR data extraction with Numba-accelerated sequence decomposition
- `src/sl_behavior/microcontrollers.py` - Parallel hardware module parsing
- `src/sl_behavior/cli.py` - Click-decorated CLI commands
- `pyproject.toml` - Project configuration and dependencies

## Notable Patterns

- Job-based processing pipeline with six distinct job types
- ProcessPoolExecutor for parallel module parsing
- Numba JIT compilation (@njit) for performance-critical code
- Polars DataFrames for efficient data manipulation
- Apache Arrow (.feather) format for output files
- MyPy strict mode with full type annotations

## Areas of Concern

- Hardware-specific log format dependencies from sl-experiment
- Cross-library coordination with sl-shared-assets for configuration dataclasses
```

---

## Usage

Invoke at session start to ensure full context before making changes. Prevents blind modifications
and ensures understanding of existing patterns.
