"""Setup configuration for Karkhana - Software Factory."""

from setuptools import setup, find_packages

setup(
    name="karkhana",
    version="0.1.0",
    description="AI-powered software development workflow orchestrator",
    author="Karkhana Team",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "langgraph>=0.1.0",
        "pydantic>=2.9.0",
        "pydantic-settings>=2.5.0",
        "openai>=1.35.0",
        "aiofiles>=24.1.0",
        "tiktoken>=0.7.0",
        "rich>=13.7.0",
        "click>=8.1.7",
        "psutil>=6.0.0",
        "ruff>=0.3.0",
        "pytest-asyncio>=0.24.0",
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.32.0",
        "websockets>=14.0",
    ],
    entry_points={
        "console_scripts": [
            "karkhana=src.main:main",
        ],
    },
)