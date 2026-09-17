#!/bin/bash
# Local testing script for HR Assistant Demo
# Run this to start the ADK web interface

/Users/aflalo/.local/bin/uv venv
source .venv/bin/activate

echo "Starting ADK web interface for local testing..."

# Ensure we are in the project directory
cd "$(dirname "$0")"

# Use the virtual environment's adk executable to avoid path resolution errors
./.venv/bin/adk web --reload_agents
