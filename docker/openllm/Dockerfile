FROM riqui/genie-in-the-box:0.3.0

RUN pip install git+https://github.com/huggingface/transformers.git@main accelerate
RUN pip install torch
RUN pip install bitsandbytes
RUN pip install scipy
# RUN pip install openllm==0.3.14
RUN pip install openllm==0.4.1
RUN pip install fairscale
# RUN pip install vllm
# RUN pip install ray

# Make sure this directory exists:
RUN mkdir -p /root/bentoml/models/pt-phind--phind-codellama-34b-v2/949f61e203f91b412efe8f679c798f09f0ff4b0c

WORKDIR /root/bentoml/models/pt-phind--phind-codellama-34b-v2/949f61e203f91b412efe8f679c798f09f0ff4b0c

# echo string to console
RUN echo "openllm start llama --model-id Phind/Phind-CodeLlama-34B-v2 --quantize int4 --backend pt -p 3000 --workers-per-resource 0.5"

# Hackey work around to max_new_token configuration: overwrite this file w/ updated configuration_llama.py file on local os
# nano /usr/local/lib/python3.10/site-packages/openllm_core/config/configuration_llama.py

# opento bash shell
CMD [ "/bin/bash" ]
# openllm start llama --model-id Phind/Phind-CodeLlama-34B-v2 --quantize int4 --backend pt -p 3000  --workers-per-resource 0.5