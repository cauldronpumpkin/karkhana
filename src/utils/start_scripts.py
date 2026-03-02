import os

def generate_start_script(framework: str, directory: str = ".") -> None:
    """Generate a start.bat or start.sh script based on the OS and framework."""
    if framework == "nextjs_fastapi":
        bat_content = """@echo off
echo Starting Karkhana Software Factory Output...
echo Booting Next.js Frontend...
start cmd /k "cd frontend && npm install && npm run dev"
echo Booting FastAPI Backend...
start cmd /k "cd backend && python -m venv venv && call venv\\Scripts\\activate && pip install -r requirements.txt && uvicorn app.main:app --reload"
echo All systems go!
"""
        sh_content = """#!/bin/bash
echo "Starting Karkhana Software Factory Output..."
echo "Booting Next.js Frontend..."
(cd frontend && npm install && npm run dev) &
echo "Booting FastAPI Backend..."
(cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload) &
echo "All systems go!"
wait
"""
        with open(os.path.join(directory, "start.bat"), "w") as f:
            f.write(bat_content)
        with open(os.path.join(directory, "start.sh"), "w") as f:
            f.write(sh_content)
        # Make sh executable
        try:
            os.chmod(os.path.join(directory, "start.sh"), 0o755)
        except Exception:
            pass
