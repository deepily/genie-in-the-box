#! /bin/bash
# This script is used to run the Genie GUI on a Mac.

# TODO: This should be a part of the environment configuration.
export OPENAI_API_KEY=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

# Activate the virtual environment
source /Users/rruiz/Projects/local-interpreter-python3.10/venv/bin/activate

# Change to the directory containing the Genie GUI
cd /Volumes/projects/genie-in-the-box/src

# Pass all command line arguments
python3.10 genie_client_gui.py "$@"
