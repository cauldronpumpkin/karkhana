# Project Structure

## Source Code
src/
├── config.py          # Configuration management
├── main.py            # CLI entry point
├── types/             # Pydantic models
│   ├── state.py       # WorkingState definition
│   ├── error.py       # ErrorLog model
│   └── project.py     # Project structure models
├── agents/            # Agent implementations
│   ├── base.py        # BaseAgent class
│   ├── pm_agent.py    # Product Manager agent
│   ├── architect_agent.py  # Architect agent
│   ├── taskmaster.py   # Task queue manager
│   ├── coder_agent.py  # Code writer
│   └── reviewer_agent.py # Code reviewer
├── sandbox/           # Safe execution environment
│   ├── executor.py    # Subprocess isolation
│   └── reporters.py   # Error parsers
├── graph/             # LangGraph state machine
│   ├── flow.py        # Graph definition
│   └── edges.py       # Routing logic
└── utils/             # Helper functions
    ├── prompts.py     # AI system prompts
    ├── parser.py      # JSON extraction
    └── logger.py      # Progress tracking

## Tests
tests/
├── test_agents.py
├── test_sandbox.py
└── test_integration.py

## Examples
examples/
├── sample_idea.txt       # Sample input idea
└── expected_output.json  # Expected file tree structure
