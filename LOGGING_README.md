# Logging System Documentation

## Overview
The Blue Psychology Test application uses a centralized logging system that provides consistent, structured logging across all components. The system is built on Python's built-in `logging` module enhanced with Rich for beautiful console output.

## Features
- Centralized logging configuration
- Rich console output with formatted tables
- Standardized AI interaction logging
- State change tracking
- Error logging with context
- Memory-efficient truncation of long messages

## Usage

### Basic Logging
```python
from app_logging import AppLogger

# Get a logger for your module
logger = AppLogger.get_logger(__name__)

# Basic logging
logger.info("Regular log message")
logger.error("Error message")
logger.warning("Warning message")
```

### AI Interaction Logging
```python
AppLogger.log_ai_interaction(
    logger=logger,
    title="Operation Name",
    system_instruction="System instruction text",
    user_input="User input text",
    context={
        "Additional Context": "Extra information",
        "More Context": "Other details"
    },
    ai_response="AI's response text"
)
```

### State Change Logging
```python
AppLogger.log_state_change(
    logger=logger,
    state_name="StateName",
    old_value="previous value",
    new_value="new value",
    context={"Additional Info": "context"}
)
```

### Error Logging
```python
try:
    # Some code that might fail
    raise ValueError("Example error")
except Exception as e:
    AppLogger.log_error(
        logger=logger,
        error=e,
        context={"Operation": "what was being attempted"}
    )
```

## Key Components
- `AppLogger`: Main class providing logging functionality
- `RichHandler`: Enhanced console output handler
- `Console`: Rich console for formatted output
- `Table`: Structured table format for complex logs

## Best Practices
1. Use the appropriate log level (INFO, WARNING, ERROR)
2. Include relevant context in log messages
3. Use structured logging for complex operations
4. Keep sensitive information out of logs
5. Use error logging with proper context for exceptions

## Configuration
The logging system is configured with:
- Basic format: `%(message)s`
- Detailed format: `[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s`
- Default level: INFO
- Rich console output enabled
- Automatic truncation of long messages
