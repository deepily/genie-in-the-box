#! /bin/bash
# This script runs the Genie GUI on my Mac(s)

# Activate the virtual environment
source /Users/rruiz/Projects/local-interpreter-python3.10/venv/bin/activate

# Change to the directory containing the Genie GUI
cd /Volumes/projects/genie-in-the-box/src

# Pass all command line arguments
python3.10 genie_client_gui.py "$@"
