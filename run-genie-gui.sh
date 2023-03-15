#! /bin/bash

# TODO: This should be a part of the environment configuration.
export OPENAI_API_KEY=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

# This script is used to run the Genie GUI on a Mac.
source /Users/rruiz/Projects/local-interpreter-python3.10/venv/bin/activate

cd /Users/rruiz/Projects/projects-sshfs/genie-server/src

# First, and only argument, is whether it should run once and exit or not.
python3.10 genie_client_gui.py "$@"