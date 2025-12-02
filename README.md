# Blue Psychology Test Bot

This project is a comprehensive Telegram bot designed for psychological testing and analysis. It leverages advanced AI models and various APIs to provide a rich user experience, including profile extraction, memory management, and PDF report generation.

## Features

-   **Psychological Testing**: Interactive tests to assess various psychological traits.
-   **AI-Powered Analysis**: Uses models like GPT-4 (via g4f) and others for deep analysis of user responses.
-   **Profile Management**: Extracts and maintains user profiles based on interactions.
-   **Memory System**: Utilizes `mem0ai` and `qdrant` for long-term memory and context retention.
-   **PDF Reports**: Generates detailed PDF reports of test results, supporting RTL languages (Persian/Arabic).
-   **Voice Interaction**: Supports voice messages and TTS (Text-to-Speech).
-   **Image Generation**: Capable of generating images based on context.
-   **Admin Dashboard**: Includes a Streamlit-based dashboard for administration and monitoring.

## Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd blue-psychology-test
    ```

2.  Create and activate a virtual environment:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  Set up environment variables:
    -   Run the interactive setup script:
        ```bash
        chmod +x setup_env.sh
        ./setup_env.sh
        ```
    -   Or manually copy `.env.example` to `.env` and edit it:
        ```bash
        cp .env.example .env
        nano .env
        ```

## Usage

### Running the Bot
To start the Telegram bot:
```bash
python telegrambot.py
```

### Running the API
To start the backend API:
```bash
python main.py
```
Or use the provided script:
```bash
./start_full_api.sh
```

### Running the Dashboard
To launch the Streamlit dashboard:
```bash
streamlit run streamlit_ui.py
```

## Project Structure

-   `telegrambot.py`: Main entry point for the Telegram bot.
-   `main.py`: FastAPI application entry point.
-   `memory/`: Contains memory management logic (`mem0`, `qdrant`).
-   `handlers/`: Telegram bot message handlers.
-   `utils.py`: Utility functions.
-   `tests/`: Unit and integration tests.
-   `html_reports/`: Templates and logic for HTML/PDF report generation.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

[License Name]
