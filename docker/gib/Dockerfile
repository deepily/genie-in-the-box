# FOR gib:0.6.0
#FROM python:3.10.12
FROM nvidia/cuda:12.2.2-base-ubuntu22.04

# install python 3.11.6
#RUN apt-get update && apt-get install -y \
#   build-essential \
#   zlib1g-dev \
#   libncurses5-dev \
#   libgdbm-dev \
#   libnss3-dev \
#   libssl-dev \
#   libreadline-dev \
#   libffi-dev \
#   libsqlite3-dev \
#   libbz2-dev \
#   wget

#RUN cd /usr/src \
#   && wget https://www.python.org/ftp/python/3.11.6/Python-3.11.6.tgz \
#   && tar -xzf Python-3.11.6.tgz \
#   && cd Python-3.11.6 \
#   && ./configure --enable-optimizations \
#   && make altinstall
#
#RUN update-alternatives --install /usr/bin/python python /usr/local/bin/python3.11 1
#RUN update-alternatives --set python /usr/local/bin/python3.11

# Install everything else
RUN apt-get update && apt-get install -y \
    && apt-get install cuda-toolkit-12-2 -y \
    && apt-get install git wget nano rsync python3-enchant pip -y \
    && apt-get install libportaudio2 libportaudiocpp0 portaudio19-dev libasound-dev libsndfile1-dev ffmpeg -y \
    && pip install pyaudio

RUN pip install -U pip

#######################################
# Specific versions needed to support web socket Io
#######################################
RUN pip install Flask==2.1.3
RUN pip install Flask-SocketIO==5.0.1
RUN pip install eventlet==0.30.2
RUN pip install Werkzeug==2.0.3
RUN pip install requests==2.31.0

RUN pip install pandas

RUN pip install pydub

RUN pip install pyperclip

RUN pip install flask_cors

RUN pip install duckduckgo-search

RUN pip install jupyterlab

RUN pip install ipywidgets

RUN pip install tabulate

RUN pip install tiktoken

RUN pip install --upgrade --no-cache-dir openai

RUN pip install --upgrade --no-cache-dir langchain[llms]

RUN pip install --upgrade --no-cache-dir wandb

RUN pip install --upgrade --no-cache-dir transformers

RUN pip install --upgrade --no-cache-dir accelerate

RUN pip install torch

RUN pip install pyaudio

RUN pip install huggingface_hub

RUN pip install wheel
# Flash attention depends upon wheel being installed
RUN pip install flash-attn --no-build-isolation

#RUN python3.11 --version
#RUN pip --version

RUN python3 -c "from huggingface_hub import snapshot_download; snapshot_download( repo_id='distil-whisper/distil-large-v2' )"

RUN pip install xmlschema

RUN pip install scikit-learn

RUN pip install openai

RUN pip install autoawq

WORKDIR /var/genie-in-the-box
RUN mkdir -p /var/io

#CMD [ "/var/genie-in-the-box/src/scripts/run-flask-gib.sh" ]
CMD [ "/bin/bash" ]
