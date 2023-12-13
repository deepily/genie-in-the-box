#! /bin/bash

# used before version two was released
# python3 TTS/server/server.py --model_name tts_models/en/ljspeech/tacotron2-DCA --vocoder_name vocoder_models/en/ljspeech/multiband-melgan --use_cuda True

python3 TTS/server/server.py --model_name tts_models/en/ljspeech/tacotron2-DDC --vocoder_name vocoder_models/en/ljspeech/hifigan_v2 --use_cuda True