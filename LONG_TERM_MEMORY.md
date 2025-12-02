# Long-term Memory System

This document describes the long-term memory system based on the exact strategy from `agent_mem0_gemini.py`, using Mem0 with local Qdrant and Ollama embeddings.

## Features

- **Mem0 Integration**: Structured memory storage and retrieval using Mem0 OSS
- **Local Qdrant**: Vector database running locally for embeddings
- **Ollama Embeddings**: Local `nomic-embed-text` model for semantic understanding
- **Rich Logging**: Detailed logging with tables showing memory search results
- **Safe Extractors**: Robust handling of different Mem0 response formats
- **Fallback Storage**: Local SQLite storage when Mem0 is unavailable

## Configuration

### Environment Variables

```bash
# Enable Mem0 long-term memory
LONGTERM_MEM0=true
```

### Prerequisites

1. **Install and run Qdrant locally:**
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```

2. **Install and run Ollama with nomic-embed-text:**
   ```bash
   # Install Ollama (see https://ollama.ai)
   ollama pull nomic-embed-text
   ```

3. **Ensure Qdrant is accessible at localhost:6333**

### Dependencies

The system requires these additional packages:
- `mem0ai` - For Mem0 OSS integration
- `langchain-ollama` - For local Ollama embeddings
- `rich` - For detailed console logging (optional)

## Usage

### Automatic Integration

When enabled via `LONGTERM_MEM0=true`, the long-term memory system automatically:

1. **Stores conversations** after each AI response using exact Mem0.add() format
2. **Retrieves relevant context** based on user queries with detailed logging
3. **Injects memory context** into system prompts as "[Mem0 Memory]" blocks

### Manual Usage

```python
from app.chat.long_term_memory import LongTermMemoryManager
from ai_utils import get_neuron_llm

# Initialize with LLM (for Mem0 processing)
llm = get_neuron_llm()
ltm = LongTermMemoryManager.from_env(user_id="user123", llm=llm)

# Add conversation (exact format from agent_mem0_gemini.py)
messages = [
    {"role": "user", "content": "What is psychology?"},
    {"role": "assistant", "content": "Psychology is the study of mind and behavior..."}
]
ltm.add_conversation_memory(messages)

# Search memories (with rich logging)
results = ltm.search_memories("psychology definition")

# Get formatted context for system prompt
context = ltm.get_relevant_context("Tell me about cognitive psychology")
# Returns: "[Mem0 Memory]\nUse if relevant:\n- Psychology is the study..."
```

### Visual Explorer

Run `streamlit run memory_mem0_ui.py` to launch the standalone Mem0/Qdrant dashboard.
The UI provides:

1. Per-user memory browsing straight from Mem0.
2. Semantic search over any user’s memories.
3. Direct Qdrant inspection (collections, metadata, payload samples).

Use the sidebar controls to point the tool to custom Qdrant hosts, ports, and collection names.

### FastAPI Endpoints

Long-term memory functionality is now accessible through the main FastAPI server.
Available routes (all scoped by `user_id`):

- `GET /memory/{user_id}` – List stored memories (Mem0 or local fallback)
- `GET /memory/{user_id}/stats` – Storage statistics
- `POST /memory/{user_id}/search` – Semantic search with body `{ "query": "...", "limit": 3 }`
- `POST /memory/{user_id}/store` – Persist a user/assistant turn `{ "user_text": "...", "assistant_text": "..." }`
- `POST /memory/{user_id}/notes` – Store free-form notes `{ "content": "...", "memory_type": "note" }`

These endpoints reuse the same `LongTermMemoryManager`, ensuring consistent behavior between the chat agent, CLI utilities, and the public API.

### User Isolation

`app/chat/smart_chat.py` now resolves the Mem0 `user_id` from the canonical `chat_id` stored in `database/users` (via `db.py`). Every Telegram user therefore gets a dedicated namespace both in Mem0 and in the SQLite fallback, keeping long-term memories neatly scoped per person regardless of which thread or device they use.

## Architecture

### Components

1. **LongTermMemoryManager**: Main class using exact agent_mem0_gemini.py strategy
2. **Mem0 OSS Client**: Local Mem0 instance with LangChain integration
3. **Local Qdrant**: Vector database running in Docker container
4. **Ollama Embeddings**: Local nomic-embed-text model (768 dimensions)
5. **Rich Logging**: Detailed tables and JSON output for debugging
6. **Local Storage**: SQLite fallback when Mem0 unavailable

### Data Flow

```
User Message → Smart Chat Agent → Mem0 Memory Manager
                     ↓                        ↓
              Generate Response ← Search Mem0 Memories
                     ↓                        ↓
              Store Interaction → Mem0.add() + Rich Logging
```

### Mem0 Configuration

Exact configuration from agent_mem0_gemini.py:

```python
mem0_config = {
    "llm": {
        "provider": "langchain",
        "config": {"model": llm}
    },
    "embedder": {
        "provider": "langchain", 
        "config": {"model": OllamaEmbeddings(model="nomic-embed-text")}
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": "localhost",
            "port": 6333,
            "collection_name": "mem0_nomic_768",
            "embedding_model_dims": 768
        }
    }
}
```

## Memory Types

### Mem0 Memory (Primary)
- Structured memory with automatic extraction using local LLM
- User-specific memory isolation via user_id
- Semantic search via local Qdrant + Ollama embeddings
- Rich logging with search results and full memory lists
- Exact configuration from agent_mem0_gemini.py

### Local Fallback
- SQLite-based storage when Mem0 unavailable
- Simple keyword matching for basic search
- Always available offline
- Automatic initialization and chunking

## Performance Considerations

### Memory Usage
- Local Ollama embeddings (no API calls)
- Local Qdrant storage (no cloud dependencies)
- Rich logging can be disabled by not installing 'rich'

### Storage Limits
- Qdrant collection grows with conversations
- Automatic chunking for large conversations
- Local SQLite fallback for basic functionality

### Network Dependencies
- No external API calls required
- All processing happens locally
- Graceful fallback to SQLite when Qdrant unavailable

## Troubleshooting

### Common Issues

1. **Mem0 Initialization Failed**
   - Ensure Qdrant is running: `docker ps` should show qdrant container
   - Check Qdrant accessibility: `curl http://localhost:6333/collections`
   - Verify Ollama is running: `ollama list` should show nomic-embed-text

2. **Qdrant Connection Failed**
   - Start Qdrant: `docker run -p 6333:6333 qdrant/qdrant`
   - Check port availability: `netstat -an | grep 6333`

3. **Ollama Embedding Failed**
   - Install Ollama: Follow instructions at https://ollama.ai
   - Pull model: `ollama pull nomic-embed-text`
   - Test model: `ollama run nomic-embed-text`

4. **Memory Search Returns Empty**
   - Check if memories were stored: Look for "Mem0.add() response" logs
   - Verify user_id consistency across sessions
   - Check Qdrant collection: Visit http://localhost:6333/dashboard

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
# Enable debug logging
import logging
logging.getLogger('app.chat.long_term_memory').setLevel(logging.DEBUG)

# Rich console logging is enabled by default when 'rich' is installed
# Look for detailed tables showing:
# - "🔎 Mem0.search() hits" with scores and content
# - "🧠 Mem0: FULL MEMORY LIST" after each addition
# - "➕ Mem0.add() response" when storing memories
```

## Security Considerations

- All data stored locally (Qdrant + SQLite)
- No external API calls or data transmission
- User data isolation enforced by user_id
- Local storage should be encrypted in production

## Future Enhancements

- Multi-modal memory support (following Mem0 roadmap)
- Advanced memory consolidation via Mem0 features
- Custom embedding models beyond nomic-embed-text
- Memory analytics and visualization
- Integration with other local LLM providers