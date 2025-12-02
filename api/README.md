# 🚀 Blue Psychology Test API

Complete REST API server for the Blue Psychology Test platform.

## 📁 Folder Structure

```
api/
├── api.py                      # Main FastAPI server
├── __init__.py                 # Python module initialization
├── README.md                   # This file
├── docs/                       # Documentation
│   ├── START_HERE_API.md       # Quick start guide
│   ├── API_README.md           # Installation & basic usage
│   ├── API_TUTORIAL.md         # Complete tutorial (2500+ lines)
│   └── API_DEVELOPMENT_SUMMARY.md  # Architecture overview
├── examples/                   # Example code
│   ├── api_client_example.py   # Python client library
│   └── api_web_demo.html       # Web interface demo
└── scripts/                    # Utility scripts
    ├── start_api.sh            # Linux/Mac startup script
    └── start_api.bat           # Windows startup script
```

## ⚡ Quick Start

### 1. Install Dependencies
```bash
# From project root
pip install -r requirements.txt
```

### 2. Start the Server

**Option A: Using Scripts (Recommended)**
```bash
# Linux/Mac
./api/scripts/start_api.sh

# Windows
api\scripts\start_api.bat
```

**Option B: Direct Execution**
```bash
# From project root
python api/api.py

# Or from api folder
cd api
python api.py
```

**Option C: Using uvicorn**
```bash
# From project root
uvicorn api.api:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access the API
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📚 Documentation

- **Start Here**: [`docs/START_HERE_API.md`](docs/START_HERE_API.md)
- **Quick Start**: [`docs/API_README.md`](docs/API_README.md)
- **Complete Tutorial**: [`docs/API_TUTORIAL.md`](docs/API_TUTORIAL.md)
- **Architecture**: [`docs/API_DEVELOPMENT_SUMMARY.md`](docs/API_DEVELOPMENT_SUMMARY.md)

## 🎯 Features

### 30+ REST Endpoints
- ✅ **Psychology Tests** - Interactive assessments
- ✅ **Smart AI Chat** - Conversational therapy
- ✅ **User Management** - Profiles & wallet
- ✅ **Image Generation** - AI personality visualizations
- ✅ **Test Packages** - Bundled offerings
- ✅ **Admin Tools** - System management

### Production Ready
- ✅ Input validation (Pydantic)
- ✅ Error handling
- ✅ Auto-generated docs (OpenAPI)
- ✅ Async support
- ✅ CORS enabled
- ✅ Health checks
- ✅ Type safety

## 🧪 Testing

### Using the Web Demo
```bash
# Open in browser
api/examples/api_web_demo.html
```

### Using Python Client
```bash
python api/examples/api_client_example.py
```

### Using cURL
```bash
# Health check
curl http://localhost:8000/health

# List tests
curl http://localhost:8000/tests
```

## 📖 Example Usage

### Python
```python
import requests

# List available tests
response = requests.get("http://localhost:8000/tests")
tests = response.json()
print(f"Available tests: {tests['count']}")

# Send chat message
response = requests.post("http://localhost:8000/chat", json={
    "user_id": "user_123",
    "message": "سلام، چطور می‌توانید کمک کنید؟"
})
print(response.json()["response"])
```

### JavaScript
```javascript
// Fetch tests
fetch('http://localhost:8000/tests')
  .then(res => res.json())
  .then(data => console.log(data.tests));

// Send chat message
fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    user_id: 'user_123',
    message: 'سلام'
  })
})
  .then(res => res.json())
  .then(data => console.log(data.response));
```

## 🚀 Deployment

See [`docs/API_TUTORIAL.md`](docs/API_TUTORIAL.md) for complete deployment guides including:
- Docker deployment
- Heroku deployment
- VPS deployment
- Nginx configuration
- Production checklist

## 🔧 Configuration

### Environment Variables
```bash
# .env file
OPENAI_API_KEY=your_gemini_api_key
OPENAI_MODEL=gemini-2.0-flash-exp
API_HOST=0.0.0.0
API_PORT=8000
```

### Database
The API uses the same SQLite database as the Telegram bot (`bot.db` in project root).
Make sure to initialize it first:
```bash
python -c "import db; db.init_db()"
```

## 📊 API Endpoints Overview

| Category | Endpoints | Description |
|----------|-----------|-------------|
| **General** | 2 | API info, health check |
| **Tests** | 7 | Test management, taking tests |
| **Users** | 6 | User profiles, wallet |
| **Chat** | 3 | Smart AI conversation |
| **Images** | 3 | Personality visualizations |
| **Packages** | 4 | Test bundles |
| **Admin** | 2 | User & system management |

**Total**: 30+ endpoints

## 🆘 Troubleshooting

### Server won't start
```bash
# Check if port is in use
lsof -i :8000

# Try a different port
uvicorn api.api:app --port 8001
```

### Database errors
```bash
# Reinitialize database
python -c "import db; db.init_db()"
```

### Import errors
```bash
# Install dependencies
pip install -r requirements.txt
```

## 📞 Support

- Check the interactive docs: http://localhost:8000/docs
- Read the tutorial: [`docs/API_TUTORIAL.md`](docs/API_TUTORIAL.md)
- Review examples: [`examples/api_client_example.py`](examples/api_client_example.py)

## 🎓 Learning Path

1. **Read**: [`docs/START_HERE_API.md`](docs/START_HERE_API.md) (5 min)
2. **Try**: Open http://localhost:8000/docs and test endpoints
3. **Run**: `python examples/api_client_example.py`
4. **Study**: [`docs/API_TUTORIAL.md`](docs/API_TUTORIAL.md) (45 min)
5. **Build**: Your own application using the API

## 🏆 What You Can Build

- 🌐 Web applications (React, Vue, Angular)
- 📱 Mobile apps (iOS, Android, React Native)
- 🖥️ Desktop applications (Electron)
- 🤖 Other bots (WhatsApp, Discord, Slack)
- 🔗 Integration with third-party services
- 📊 Analytics dashboards
- 🧪 Research platforms

## 📝 License

Same as the main project.

---

**Quick Start Command:**
```bash
python api/api.py
```

Then visit: http://localhost:8000/docs 🚀
