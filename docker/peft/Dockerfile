# v0.1.0 was:
# FROM nvidia/cuda:12.2.0-base-ubuntu22.04
# v0.2.0 is:
FROM nvidia/cuda:12.2.2-base-ubuntu22.04

RUN apt-get update && apt-get install -y \
    && apt-get install git wget nano rsync python3-enchant pip -y \
    && apt-get install libportaudio2 libportaudiocpp0 portaudio19-dev libasound-dev libsndfile1-dev ffmpeg cuda-toolkit-12-2 -y \
    && pip3 install pyaudio

RUN pip install -U pip

RUN pip install bitsandbytes
RUN pip install git+https://github.com/huggingface/transformers.git
RUN pip install git+https://github.com/huggingface/peft.git
RUN pip install git+https://github.com/huggingface/accelerate.git
RUN pip install datasets
RUN pip install torch
RUN pip install peft
RUN pip install scipy
RUN pip install jupyterlab
RUN pip install ipywidgets
RUN pip install sentencepiece
RUN pip install protobuf
RUN pip install flash-attn --no-build-isolation
RUN pip install trl
RUN pip install wandb
RUN pip install xmltodict
RUN pip install xmlschema
RUN pip install scikit-learn
RUN pip install tiktoken

RUN pip install openai

CMD [ "/bin/bash" ]