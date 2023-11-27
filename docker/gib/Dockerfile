# FOR gib:0.4.0
#FROM python:3.10.12
FROM nvidia/cuda:12.2.0-base-ubuntu22.04

# install python 3.11.6
RUN apt-get update && apt-get install -y \
   build-essential \
   zlib1g-dev \
   libncurses5-dev \
   libgdbm-dev \
   libnss3-dev \
   libssl-dev \
   libreadline-dev \
   libffi-dev \
   libsqlite3-dev \
   libbz2-dev \
   wget

RUN cd /usr/src \
   && wget https://www.python.org/ftp/python/3.11.6/Python-3.11.6.tgz \
   && tar -xzf Python-3.11.6.tgz \
   && cd Python-3.11.6 \
   && ./configure --enable-optimizations \
   && make altinstall

RUN update-alternatives --install /usr/bin/python python /usr/local/bin/python3.11 1
RUN update-alternatives --set python /usr/local/bin/python3.11

# Install everything else except pyaudio which is now failing :-(
RUN apt-get update && apt-get install -y \
    && apt-get install cuda-toolkit-12-2 -y \
    && apt-get install git wget nano rsync python3-enchant pip -y \
    && apt-get install libportaudio2 libportaudiocpp0 portaudio19-dev libasound-dev libsndfile1-dev ffmpeg -y
#    && pip install pyaudio \

RUN pip3.11 install -U pip

#######################################
# Specific versions needed to support web socket Io
#######################################
RUN pip3.11 install Flask==2.1.3
RUN pip3.11 install Flask-SocketIO==5.0.1
RUN pip3.11 install eventlet==0.30.2
RUN pip3.11 install Werkzeug==2.0.3
RUN pip3.11 install requests==2.31.0

RUN pip3.11 install pandas

RUN pip3.11 install pydub

RUN pip3.11 install pyperclip

RUN pip3.11 install flask_cors

RUN pip3.11 install duckduckgo-search

# RUN pip3.11 install openai-whisper

RUN pip3.11 install jupyterlab

RUN pip3.11 install ipywidgets

RUN pip3.11 install tabulate

RUN pip3.11 install tiktoken

RUN pip3.11 install --upgrade --no-cache-dir openai

RUN pip3.11 install --upgrade --no-cache-dir langchain[llms]

RUN pip3.11 install --upgrade --no-cache-dir wandb

RUN pip3.11 install --upgrade --no-cache-dir transformers

RUN pip3.11 install --upgrade --no-cache-dir accelerate

RUN pip3.11 install torch

RUN pip3.11 install pyaudio

RUN pip3.11 install huggingface_hub

RUN pip3.11 install wheel
# Flash attention depends upon wheel being installed
RUN pip3.11 install flash-attn --no-build-isolation

RUN python3.11 --version
RUN pip3.11 --version

RUN python3.11 -c "from huggingface_hub import snapshot_download; snapshot_download( repo_id='distil-whisper/distil-large-v2' )"

WORKDIR /var/genie-in-the-box
RUN mkdir -p /var/io

CMD [ "/var/genie-in-the-box/src/scripts/run-flask-gib.sh" ]
#CMD [ "/bin/bash" ]
