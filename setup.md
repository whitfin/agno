install vllm from source (cpu - only)
vllm serve "microsoft/Phi-3-mini-4k-instruct"


# for serving zephyr-7b-beta model
#vllm serve HuggingFaceH4/zephyr-7b-beta \
#   --dtype float32 \
#   --enable-auto-tool-choice \
#   --tool-call-parser pythonic


# vllm serve mistralai/Mistral-7B-Instruct-v0.2 \
#   --dtype float32 \
#   --enable-auto-tool-choice \
#   --tool-call-parser mistral \
#   --hf-token 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