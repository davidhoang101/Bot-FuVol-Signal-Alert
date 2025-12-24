#!/bin/bash
# Start backend server

cd backend
source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt --quiet
python -m app.main
