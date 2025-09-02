# OllamaTools Cookbook

> Note: Fork and clone this repository if needed

### 1. [Install](https://github.com/ollama/ollama?tab=readme-ov-file#macos) ollama and run models

Run your chat model

```shell
ollama pull llama3.2
```

### 2. Create and activate a virtual environment

```shell
python3 -m venv ~/.venvs/aienv
source ~/.venvs/aienv/bin/activate
```

### 3. Install libraries

```shell
pip install -U ollama ddgs duckdb yfinance agno
```

### 4. Run basic Agent

- Streaming on

```shell
python cookbook/models/ollama_tools/basic_stream.py
```

- Streaming off

```shell
python cookbook/models/ollama_tools/basic.py
```

### 5. Run Agent with Tools

- DuckDuckGo Search

```shell
python cookbook/models/ollama_tools/tool_use.py
```

### 6. Run Agent that returns structured output

```shell
python cookbook/models/ollama_tools/structured_output.py
```

### 7. Run Agent that uses storage

```shell
python cookbook/models/ollama_tools/storage.py
```

### 8. Run Agent that uses knowledge

```shell
python cookbook/models/ollama_tools/knowledge.py
```
