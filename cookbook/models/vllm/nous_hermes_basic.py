"""Quick start with Nous-Hermes-2 (Mistral-7B-DPO) running on vLLM.

Prerequisites
-------------
Launch the server (needs ~10 GB RAM for 8 K context, increase VLLM_CPU_KVCACHE_SPACE for larger):

```bash
# 8 K context on CPU
vllm serve NousResearch/Nous-Hermes-2-Mistral-7B-DPO \
  --dtype float32 \
  --max-model-len 8192 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

Then run this script.
"""

from agno.agent import Agent
from agno.models.vllm import Vllm

agent = Agent(
    model=Vllm(id="NousResearch/Nous-Hermes-2-Mistral-7B-DPO"),
    markdown=True,
)

agent.print_response("Give me a haiku about open-source AI.") 