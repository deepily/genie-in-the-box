#! /bin/bash
# This script runs the Genie GUI on my Mac(s)

# Activate the virtual environment
source /Users/rruiz/Projects/local-interpreter-python3.10/venv/bin/activate

# Change to the directory containing the Genie GUI
# Using SMB mount:
# cd /Volumes/projects/genie-in-the-box/src
# Using SSHFS:
cd /Users/rruiz/Projects/projects-sshfs/genie-in-the-box/src

#GENIE_IN_THE_BOX_ROOT=/Users/rruiz/Projects/projects-sshfs/genie-in-the-box/src
#export GENIE_IN_THE_BOX_ROOT

# Pass all command line arguments
python3.10 genie_client_gui.py "$@"
