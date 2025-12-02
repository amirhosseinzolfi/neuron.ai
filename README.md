# Blue Psychology Test Bot 🧠

An advanced AI-powered Telegram bot for comprehensive psychological assessments with multimodal support (text, voice, images).

## Features

- 🎯 **Multiple Psychology Tests**: MBTI, DISC, Big Five, and more
- 🤖 **AI-Powered Analysis**: Advanced LLM-based personality profiling
- 🎙️ **Voice Support**: Text-to-speech results and voice input
- 🖼️ **Image Generation**: AI-generated personality visualizations
- 📊 **Rich Reports**: PDF, HTML, and interactive reports
- 💾 **Long-term Memory**: Persistent user profiles with Mem0
- 💰 **Payment System**: Integrated wallet and package management
- 🔒 **Secure**: Environment-based configuration

## Architecture

```
blue-psychology-test/
├── app/                    # FastAPI application
│   ├── api/               # API routers
│   ├── chat/              # Smart chat & memory
│   └── services/          # Business logic
├── database/              # User data & profiles
├── handlers/              # Telegram handlers
├── tools/                 # Utilities (TTS, etc.)
├── api/                   # Standalone API
└── frontend/              # Web interface
```

## Quick Start

### Prerequisites

- Python 3.10+
- Telegram Bot Token
- OpenAI/G4F API access

### Installation

```bash
# Clone repository
git clone <repository-url>
cd blue-psychology-test

# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "import db; db.init_db()"

# Run bot
python telegrambot.py
```

### Environment Variables

```env
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=http://localhost:15207/v1
OPENAI_MODEL=gemini-2.5-flash
```

## API Usage

Start the API server:

```bash
python run_api.py
```

Access API documentation at `http://localhost:8000/docs`

### Example API Call

```bash
curl -X POST "http://localhost:8000/api/profile/extract" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "conversation": "I am an introvert..."}'
```

## Components

### Telegram Bot
- Multi-user concurrent processing
- Persistent keyboard navigation
- Admin panel for user management
- Payment verification system

### Smart Chat
- Context-aware conversations
- Long-term memory integration
- Personality-based responses
- Multimodal input support

### Profile Extraction
- Automated personality profiling
- JSON schema validation
- Incremental profile updates
- Multi-source data aggregation

### Report Generation
- PDF reports with RTL support
- HTML interactive reports
- Voice narration
- AI-generated imagery

## Development

### Running Tests

```bash
# Profile extraction
python test_profile_extractor.py

# API endpoints
python test_image_api.py

# Integration tests
python test_integration_profile.py
```

### Service Management

```bash
# Install as systemd service
sudo ./install_service.sh

# Manage service
sudo systemctl start blue-psychology-api
sudo systemctl status blue-psychology-api
```

## Tech Stack

- **Bot Framework**: python-telegram-bot
- **API**: FastAPI + Uvicorn
- **AI/LLM**: LangChain, G4F, OpenAI
- **Memory**: Mem0, Qdrant
- **Database**: SQLite + SQLAlchemy
- **Documents**: WeasyPrint, ReportLab
- **UI**: Streamlit, Flask

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Support

For issues and questions, please open a GitHub issue.
