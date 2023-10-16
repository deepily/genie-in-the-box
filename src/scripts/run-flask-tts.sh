#! /bin/bash

# cd /var/genie-in-the-box/src

# python3 TTS/server/server.py --use_cuda True
python3 TTS/server/server.py --model_name tts_models/en/ljspeech/tacotron2-DCA --vocoder_name vocoder_models/en/ljspeech/multiband-melgan --use_cuda True