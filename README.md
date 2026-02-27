# Karkhana - Local Software Factory

A local, autonomous, multi-agent software factory inspired by bolt.new.

## Overview

Karkhana ingests raw product ideas and outputs fully functional codebases using:
- **Qwen 3 Coder Next** via LM Studio (localhost:1234/v1)
- **Next.js App Router** for frontend
- **FastAPI** for Python backend
- **SQLite** as default database

## Architecture

```
Raw Idea → PM Agent → Architect Agent → Taskmaster → 
Coder + Reviewer + Sandbox Loop → Complete Codebase
```

### Agents
1. **PM Agent**: Generates structured PRD from raw idea
2. **Architect Agent**: Defines tech stack and file tree
3. **Taskmaster**: Manages implementation queue
4. **Coder Agent**: Writes production-ready code
5. **Reviewer Agent**: Validates syntax, imports, hallucinations

### Sandbox
- Isolated subprocess execution
- No Docker required
- Safe resource limits
- Automatic error parsing

## Installation

### Option 1: Install as a package (recommended)

```bash
pip install -e .
```

### Option 2: Install dependencies manually

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your LM Studio settings
```

## Usage

### Using the CLI command (after installing as package):

```bash
karkhana "Your product idea here" --output-dir my_project
```

### Using Python module:

```bash
python -m src.main "Your product idea here" --output-dir my_project
```

## Directory Structure

See `examples/README_EXAMPLES.md` for full structure.

## Self-Healing Loop

1. Coder writes file
2. Reviewer checks quality
3. Sandbox runs tests/linter
4. If error → Coder fixes based on traceback
5. Loop until success

## Configuration

Edit `.env`:
```
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_MODEL_NAME=qwen-3-coder-next
MAX_TOKENS=8192
TEMPERATURE_CREATIVE=0.7
TEMPERATURE_CODING=0.2
SANDBOX_TIMEOUT=120
```

## Output

Generates complete project with:
- Full Next.js App Router frontend
- FastAPI Python backend
- SQLite database setup
- Testing suites (pytest + Jest)
- GitHub Actions workflows
- README.md with setup instructions
- Docker support files
