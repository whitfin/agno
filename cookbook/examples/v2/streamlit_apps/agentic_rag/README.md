# Agentic RAG Agent v2.0

**Agentic RAG Agent v2.0** is an enhanced chat application that combines models with retrieval-augmented generation using Agno v2 primitives.
It allows users to ask questions based on custom knowledge bases, documents, and web data, retrieve context-aware answers, and maintain chat history across sessions with advanced memory capabilities.

> Note: Fork and clone this repository if needed

### 1. Create a virtual environment

```shell
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```shell
pip install -r cookbook/examples/v2/streamlit_apps/agentic_rag/requirements.txt
```

### 3. Configure API Keys

Required:
```bash
export OPENAI_API_KEY=your_openai_key_here
```

Optional (for additional models):
```bash
export ANTHROPIC_API_KEY=your_anthropic_key_here
export GOOGLE_API_KEY=your_google_key_here
export GROQ_API_KEY=your_groq_key_here
```

### 4. Run PgVector

> Install [docker desktop](https://docs.docker.com/desktop/install/mac-install/) first.

- Run using a helper script

```shell
./cookbook/scripts/run_pgvector.sh
```

- OR run using the docker run command

```shell
docker run -d \
  -e POSTGRES_DB=ai \
  -e POSTGRES_USER=ai \
  -e POSTGRES_PASSWORD=ai \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v pgvolume:/var/lib/postgresql/data \
  -p 5532:5432 \
  --name pgvector \
  agnohq/pgvector:16
```

### 5. Test the v2.0 Implementation (Optional)

Before running the app, you can test that all v2 primitives are working correctly:

```shell
cd cookbook/examples/v2/streamlit_apps/agentic_rag
python test_v2.py
```

This will validate that the Knowledge, Memory, and Storage systems are properly configured.

### 6. Run Agentic RAG v2.0 App

```shell
streamlit run cookbook/examples/v2/streamlit_apps/agentic_rag/app.py 
```

## 🆕 What's New in v2.0

### Enhanced Primitives
- **Knowledge System v2**: Separated document store and vector store with enhanced metadata support
- **Memory System v2**: Pluggable memory backends with user memories and session summaries
- **Storage System v2**: Improved session management and persistence

### Key Improvements
- **Better Document Processing**: Using `DocumentV2` with rich metadata support
- **Advanced Memory Management**: User preferences and conversation history with `enable_user_memories`
- **Session Summaries**: Automatic session summarization with `enable_session_summaries`
- **Enhanced Knowledge Search**: Improved search with source attribution and metadata awareness

### Migration from v1
- Replaced `AgentKnowledge` with `Knowledge` class
- Replaced `PostgresAgentStorage` with `PostgresStorage` and `Memory` system
- Updated document processing to use `DocumentV2` format
- Enhanced agent instructions to leverage v2 memory features

## 🔧 Customization

### Model Selection

The application supports multiple model providers:
- OpenAI (o3-mini, gpt-4o)
- Anthropic (claude-3-5-sonnet)
- Google (gemini-2.0-flash-exp)
- Groq (llama-3.3-70b-versatile)

### How to Use
- Open [localhost:8501](http://localhost:8501) in your browser.
- Upload documents or provide URLs (websites, csv, txt, and PDFs) to build a knowledge base.
- Enter questions in the chat interface and get context-aware answers.
- The app can also answer question using duckduckgo search without any external documents added.

### Troubleshooting
- **Docker Connection Refused**: Ensure `pgvector`  containers are running (`docker ps`).
- **OpenAI API Errors**: Verify that the `OPENAI_API_KEY` is set and valid.

## 📚 Documentation

For more detailed information:
- [Agno Documentation](https://docs.agno.com)
- [Streamlit Documentation](https://docs.streamlit.io)

## 🤝 Support

Need help? Join our [Discord community](https://agno.link/discord)



