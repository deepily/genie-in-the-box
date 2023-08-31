# FOR whisper:0.1.0
FROM riqui/mimape:0.1.0

RUN pip3 install openai-whisper

RUN apt-get update \
        && apt-get install libportaudio2 libportaudiocpp0 portaudio19-dev libasound-dev libsndfile1-dev -y \
        && pip3 install pyaudio

RUN pip3 install pydub

RUN pip3 install --upgrade openai

RUN pip3 install pyperclip

RUN pip3 install flask_cors

RUN pip3 install pip install duckduckgo-search

CMD [ "/var/genie-in-the-box/run-flask-whisper.sh" ]

