#!/bin/bash
source ./.agent_venv/bin/activate
python src/agent.py download-files
python src/agent.py start