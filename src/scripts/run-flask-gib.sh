#! /bin/bash

cd /var/genie-in-the-box/src

export FLASK_DEBUG=1
export GIB_FLASK_CLI_ARGS="config_path=/src/conf/gib-app.ini splainer_path=/src/conf/gib-app-splainer.ini config_block_id=Genie+in+the+Box:+Development"

flask run --port 7999 --host 0.0.0.0