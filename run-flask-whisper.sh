#! /bin/bash

# ¡kluge! fix in the Dockerfile to get the flask app to run
#pip install flask_cors

cd /var/genie-in-the-box/src

flask --debug run --port 7999 --host 0.0.0.0