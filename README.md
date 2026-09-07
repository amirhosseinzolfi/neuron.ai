# Neuron AI — Psychology Test Bot 🧠

An AI-powered Telegram bot for comprehensive psychological assessments with multimodal support (text, voice, images).

## Features

- 🎯 **Multiple Psychology Tests** — MBTI, DISC, Big Five, and more
- 🤖 **AI-Powered Analysis** — LLM-based personality profiling via Google Gemini / G4F
- 🎙️ **Voice Support** — Text-to-speech results and voice input
- 🖼️ **Image Generation** — AI-generated personality visualizations
- 📊 **Rich Reports** — PDF (RTL-ready) and HTML interactive reports
- 💾 **Long-term Memory** — Persistent user profiles via Mem0 + Qdrant
- 💰 **Payment System** — Integrated wallet and package management
- 🔒 **Secure** — Environment-based configuration, no secrets in code

## Project Structure

```
neuron/
├── app/                        # FastAPI application
│   ├── api/                    # Route handlers (chat, TTS, image, memory, profile, reports)
│   ├── chat/                   # Smart chat & memory integration
│   └── services/               # Business logic (TTS, image, memory, profile extraction)
├── api/                        # Standalone REST API (full bot API surface)
├── database/                   # SQLite DB + profile/schema files
├── handlers/                   # Telegram update handlers
├── tools/                      # Utilities (text-to-voice)
├── tests/                      # Test suite
├── frontend/                   # Web UI (HTML/CSS)
├── assets/                     # Static assets (CSS)
├── images/                     # Bot images (MBTI, DISC)
├── telegrambot.py              # Bot entry point
├── ai_utils.py                 # LLM interaction layer
├── db.py                       # Database access layer
├── prompts.py                  # System prompts
├── telegram_handlers.py        # Core Telegram handlers
├── telegram_ui.py              # UI helpers
├── pdf_utils.py                # PDF generation
├── html_utils.py               # HTML report generation
├── memory0.py                  # Mem0 integration
└── run_api.py                  # API server entry point
```

## Quick Start

### Prerequisites

- Python 3.10+
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- Google Gemini API key ([makersuite.google.com](https://makersuite.google.com/app/apikey))
- Qdrant running locally (for long-term memory)
- Ollama running locally (for embeddings)

### Installation

```bash
git clone https://github.com/amirhosseinzolfi/neuron.ai.git
cd neuron.ai

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your actual credentials

python -c "import db; db.init_db()"

python telegrambot.py
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
GOOGLE_API_KEY=your_google_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_BASE_URL=http://localhost:15207/v1
OPENAI_MODEL=gemini-flash-latest
```

See `.env.example` for the full list of configuration options.

## Running the API Server

```bash
python run_api.py
# Docs at http://localhost:8000/docs
```

### Example

```bash
curl -X POST "http://localhost:8000/api/profile/extract" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "conversation": "I am an introvert..."}'
```

## Running the Bot + API Together

```bash
bash start_neuron.sh
```

## Running Tests

```bash
pytest tests/
```

## Tech Stack

| Layer | Technology |
|---|---|
| Bot Framework | python-telegram-bot 13.x |
| API | FastAPI + Uvicorn |
| AI/LLM | LangChain, Google Gemini, G4F |
| Memory | Mem0 + Qdrant + Ollama embeddings |
| Database | SQLite + SQLAlchemy |
| PDF | WeasyPrint (RTL support) |
| UI | Streamlit |

## License

MIT License
