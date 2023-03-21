#! /bin/bash

# TODO: This should be a part of the environment configuration.
export OPENAI_API_KEY=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

# This script is used to run the Genie GUI on a Mac.
source /Users/rruiz/Projects/local-interpreter-python3.10/venv/bin/activate

cd /Users/rruiz/Projects/projects-sshfs/genie-in-the-box/src

# Pass all command line arguments
python3.10 genie_client_gui.py "$@"
