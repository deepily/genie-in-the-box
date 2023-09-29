# FOR gib:0.3.0
FROM python:3.10.12

RUN apt-get update && apt-get install -y \
    && apt-get install git wget nano rsync python3-enchant pip -y \
    && apt-get install libportaudio2 libportaudiocpp0 portaudio19-dev libasound-dev libsndfile1-dev ffmpeg -y \
    && pip3 install pyaudio

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

RUN pip3 install pydub

RUN pip3 install pyperclip

RUN pip3 install flask_cors

RUN pip3 install duckduckgo-search

RUN pip3 install openai-whisper

RUN pip3 install jupyterlab
#RUN pip3 install notebook
RUN pip3 install ipywidgets

RUN pip3 install tabulate

RUN pip install tiktoken

RUN pip3 install --upgrade --no-cache-dir openai

RUN pip install --upgrade --no-cache-dir langchain[llms]

RUN pip install --upgrade --no-cache-dir wandb

WORKDIR /var/genie-in-the-box
# Superfluous?
# RUN mkdir -p WORKDIR
RUN mkdir -p /var/io

# This isn't working
## Switch to run as a non-root user
#RUN groupadd -r rruiz && useradd -r -g rruiz rruiz
#USER rruiz

# TODO: This throws an error
#WORKDIR /var/genie-in-the-box
#RUN chown -R rruiz:rruiz /var/genie-in-the-box

CMD [ "/var/genie-in-the-box/run-flask-whisper.sh" ]
#CMD [ "/bin/bash" ]
