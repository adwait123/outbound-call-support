#!/bin/bash
python3 -m venv .agent_venv
source .agent_venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate