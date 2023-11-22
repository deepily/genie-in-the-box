#! /bin/bash
# This script runs the Genie GUI on my Mac(s)

# Activate the virtual environment
source ~/Projects/local-interpreter-python3.10/venv/bin/activate

# Change to the directory containing the Genie GUI using SSHFS:
cd ~/Projects/projects-sshfs/genie-in-the-box/src
# echo "Current directory: $(pwd)"

GENIE_IN_THE_BOX_ROOT=~/Projects/projects-sshfs/genie-in-the-box
export GENIE_IN_THE_BOX_ROOT

# Pass all command line arguments
python3.10 lib/clients/genie_client_gui.py "$@"
