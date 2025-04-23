# Blue Psychology Test

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)](https://core.telegram.org/bots)

---

## Overview

**Blue Psychology Test** is a modular Python toolkit and Telegram Bot designed to deliver interactive psychology assessments via CLI, web UI (ChainLit), and Telegram. It leverages open‑source AI models for dynamic content generation, secure logging, and flexible workflows.

Key components:

- **CLI Module** (`psychology_test.py`): Run interactive prompts locally.
- **ChainLit UI** (`psychology-test-chainlit.py`): Launch a browser-based interface for real-time testing.
- **Telegram Bot** (`telegram_bot.py`): Interact with users over Telegram, delivering tests and collecting responses.
- **Prompts Definitions** (`prompts.py`): Centralized question bank and configuration.


## Table of Contents

1. [Features](#features)
2. [Getting Started](#getting-started)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Project Structure](#project-structure)
6. [Contributing](#contributing)
7. [License](#license)


## Features

- 🎯 **Modular Design**: Easily swap or extend question flows.
- 🌐 **Multi-Platform**: CLI, ChainLit web UI, and Telegram Bot support.
- 🔒 **Secure Logging**: Configurable HAR & cookie storage for audit trails.
- ⚙️ **AI-Powered**: Plug-in OpenAI or local LLM backends for dynamic content.


## Getting Started

### Prerequisites

- Python 3.12 or higher
- Git client
- Telegram Bot token (via @BotFather)
- (Optional) OpenAI API key or other LLM credentials


### Installation

```bash
# 1. Clone the repository
git clone https://github.com/amirhosseinzolfi/blue-psychology-test.git
cd blue-psychology-test

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate     # Linux/macOS
.venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```


## Configuration

1. Copy and rename `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

2. Populate environment variables:

   ```ini
   TELEGRAM_TOKEN=your_telegram_bot_token
   OPENAI_API_KEY=your_openai_api_key  # if using OpenAI backend
   LOG_DIR=har_and_cookies
   ```

3. (Optional) Adjust prompt settings in `prompts.py`.


## Usage

### 1. CLI Testing

```bash
python psychology_test.py
```

### 2. ChainLit Web UI

```bash
python psychology-test-chainlit.py
# Navigate to http://localhost:8000 in your browser
```

### 3. Telegram Bot

```bash
python telegram_bot.py
# Start your bot on Telegram and send /start to begin
```


## Project Structure

```
├── prompts.py                  # Question definitions and settings
├── psychology_test.py          # CLI entry point
├── psychology-test-chainlit.py # Web UI via ChainLit
├── telegram_bot.py             # Telegram Bot integration
├── requirements.txt            # Python dependencies
├── har_and_cookies/            # Secure logs (HAR, cookies)
└── README.md                   # Project documentation
```


## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/foo`)
3. Commit your changes (`git commit -am 'Add foo feature'`)
4. Push to branch (`git push origin feature/foo`)
5. Open a Pull Request

Please ensure code quality with `flake8` and `black` before submitting.


## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.


## Contact

Maintained by [amirhosseinzolfi](https://github.com/amirhosseinzolfi) — feel free to open issues or PRs!
