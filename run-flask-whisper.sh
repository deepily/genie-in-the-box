#! /bin/bash

# ¡kluge! fix in the Dockerfile to get the flask app to run
pip install pyperclip

cd /var/genie-server/src

flask run --port 7999 --host 0.0.0.0