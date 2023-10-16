#! /bin/bash

cd /var/genie-in-the-box/src

export FLASK_DEBUG=1

flask run --port 7999 --host 0.0.0.0