#!/bin/bash
set -e

# Auto-seed the database if empty
echo "Checking database state..."
python seed.py

# Start the server (main.py creates FastAPI app inside main())
echo "Starting server..."
exec python main.py
