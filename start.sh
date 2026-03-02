#!/bin/bash
echo "Starting Karkhana Software Factory Output..."
echo "Booting Next.js Frontend..."
(cd frontend && npm install && npm run dev) &
echo "Booting FastAPI Backend..."
(cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload) &
echo "All systems go!"
wait
