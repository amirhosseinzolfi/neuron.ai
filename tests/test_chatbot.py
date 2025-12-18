import os
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# from g4f.cookies import set_cookies_dir, read_cookie_files
import g4f.debug

# from g4f.cookies import set_cookies_dir, read_cookie_files
# g4f.debug.logging = True
# set_cookies_dir("har_and_cookies")
# read_cookie_files("har_and_cookies")
# print("HAR/cookies loaded OK")

g4f.debug.logging = True

# set_cookies_dir("har_and_cookies")
# read_cookie_files("har_and_cookies")
# --------------------------
# G4F API Server Bootstrap
# --------------------------
try:
    from g4f.api import run_api
except ImportError:
    run_api = None

if run_api:
    def _start_g4f():
        logging.info("Starting G4F API server on http://localhost:1555/v1 ...")
        try:
            run_api(bind="0.0.0.0:1555")
        except Exception as e:
            logging.error(f"Error starting G4F API: {e}")
    threading.Thread(target=_start_g4f, daemon=True, name="G4F-API-Thread").start()
else:
    logging.warning("g4f.api module not found. Install the 'g4f' package to run the local API server.")

# --------------------------
# Terminal Chatbot Script
# --------------------------
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ANSI escape codes for colors
class Colors:
    USER  = '\033[92m'  # Green
    BOT   = '\033[94m'  # Blue
    ERROR = '\033[91m'  # Red
    INFO  = '\033[93m'  # Yellow
    ENDC  = '\033[0m'   # Reset

AVAILABLE_MODELS = [
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemma-3-27b-it",
    "gemini-1.5-pro",
    "gemini-2.0-pro",
    "gpt-4o",
    "gpt-5-mini",
    "gpt-5-thinking",
    "gpt-5-nano",
    "gpt-5-chat",
    "gpt-5-mini-high",
    "gpt-5-high",
    "gpt-5-chat",
    "gpt-4.5",
    "gpt-4.1-mini",
    "gpt-5",
    "gpt-4.1",
    "gpt-4o-mini",
    "o1",
    "o3-mini",
    "llama-3.3-70b",
    "llama-4-scout",
    "deepseek-r1",
    "claude-3.5-sonnet",
    "claude-3.7-sonnet",
]

def select_model():
    print(f"{Colors.INFO}Please select an LLM model to use:{Colors.ENDC}")
    for i, model_name in enumerate(AVAILABLE_MODELS):
        print(f"{Colors.INFO}{i + 1}. {model_name}{Colors.ENDC}")

    while True:
        try:
            choice = input(f"{Colors.USER}Enter the number of the model: {Colors.ENDC}").strip()
            model_index = int(choice) - 1
            if 0 <= model_index < len(AVAILABLE_MODELS):
                logging.info(f"Model selected: {AVAILABLE_MODELS[model_index]}")
                return model_index
            else:
                print(f"{Colors.ERROR}Invalid selection. Please enter a number between 1 and {len(AVAILABLE_MODELS)}.{Colors.ENDC}")
                logging.warning(f"Invalid model selection: {choice}")
        except ValueError:
            print(f"{Colors.ERROR}Invalid input. Please enter a number.{Colors.ENDC}")
            logging.error(f"Invalid input: {choice}", exc_info=True)
        except Exception as e:
            print(f"{Colors.ERROR}An error occurred: {e}{Colors.ENDC}")
            logging.exception("An error occurred during model selection")


def main_chat_loop():
    selected_model_index = select_model()
    if selected_model_index is None:
        logging.info("No model selected, exiting.")
        return

    selected_model_name = AVAILABLE_MODELS[selected_model_index]
    print(f"{Colors.INFO}Initializing ChatBot LLM with model: {selected_model_name}…{Colors.ENDC}")
    logging.info(f"Initializing ChatBot LLM with model: {selected_model_name}")
    try:
        llm = ChatOpenAI(
            base_url="http://46.249.101.240:15203/v1",
            model_name=selected_model_name,
            temperature=0.5,
            api_key="11"  # replace with a valid key if needed
        )
        logging.info("ChatOpenAI initialized successfully.")

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant."),
            ("human", "{user_input}")
        ])
        parser = StrOutputParser()
        chain = prompt | llm | parser

        print(f"{Colors.INFO}ChatBot ready. Type 'quit' to exit.{Colors.ENDC}")
        print(f"{Colors.INFO}{'-'*30}{Colors.ENDC}")
        logging.info("ChatBot ready for interaction.")

    except Exception as e:
        print(f"{Colors.ERROR}Initialization error: {e}{Colors.ENDC}")
        logging.exception("Error during ChatBot initialization")
        return

    while True:
        try:
            user_input = input(f"{Colors.USER}You: {Colors.ENDC}").strip()
            if user_input.lower() in ("quit", "exit"):
                print(f"{Colors.INFO}Goodbye!{Colors.ENDC}")
                logging.info("User exited the chat.")
                break
            if not user_input:
                continue

            logging.info(f"User input: {user_input}")
            response = chain.invoke({"user_input": user_input})
            print(f"{Colors.BOT}Bot: {response}{Colors.ENDC}")
            logging.info(f"Bot response: {response}")

        except ConnectionError as ce:
            print(f"{Colors.ERROR}Connection error: {ce}{Colors.ENDC}")
            logging.error(f"Connection error: {ce}")
        except Exception as e:
            print(f"{Colors.ERROR}Error: {e}{Colors.ENDC}")
            logging.exception("An error occurred during chat interaction")

if __name__ == "__main__":
    main_chat_loop()
from langchain_core.output_parsers import StrOutputParser

# ANSI escape codes for colors
class Colors:
    USER  = '\033[92m'  # Green
    BOT   = '\033[94m'  # Blue
    ERROR = '\033[91m'  # Red
    INFO  = '\033[93m'  # Yellow
    ENDC  = '\033[0m'   # Reset

AVAILABLE_MODELS = [
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash",

    "gemini-1.5-pro",
    "gemini-2.0-pro",
    "gpt-4o",
    "gpt-5-mini",
    "gpt-5",
    "gpt-4.1",
    
    "gpt-4o-mini",
    "o1",
    "o3-mini",
    "llama-3.3-70b",
    "deepseek-r1",
    "claude-3.5-sonnet",
    "claude-3.7-sonnet",
]

def select_model():
    print(f"{Colors.INFO}Please select an LLM model to use:{Colors.ENDC}")
    for i, model_name in enumerate(AVAILABLE_MODELS):
        print(f"{Colors.INFO}{i + 1}. {model_name}{Colors.ENDC}")

    while True:
        try:
            choice = input(f"{Colors.USER}Enter the number of the model: {Colors.ENDC}").strip()
            model_index = int(choice) - 1
            if 0 <= model_index < len(AVAILABLE_MODELS):
                return model_index
            else:
                print(f"{Colors.ERROR}Invalid selection. Please enter a number between 1 and {len(AVAILABLE_MODELS)}.{Colors.ENDC}")
        except ValueError:
            print(f"{Colors.ERROR}Invalid input. Please enter a number.{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.ERROR}An error occurred: {e}{Colors.ENDC}")


def main_chat_loop():
    selected_model_index = select_model()
    if selected_model_index is None:
        return

    selected_model_name = AVAILABLE_MODELS[selected_model_index]
    print(f"{Colors.INFO}Initializing ChatBot LLM with model: {selected_model_name}…{Colors.ENDC}")
    try:
        llm = ChatOpenAI(
            base_url="http://localhost:1555/v1",
            model_name=selected_model_name,
            temperature=0.5,
            api_key="11"  # replace with a valid key if needed
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant."),
            ("human", "{user_input}")
        ])
        parser = StrOutputParser()
        chain = prompt | llm | parser

        print(f"{Colors.INFO}ChatBot ready. Type 'quit' to exit.{Colors.ENDC}")
        print(f"{Colors.INFO}{'-'*30}{Colors.ENDC}")

    except Exception as e:
        print(f"{Colors.ERROR}Initialization error: {e}{Colors.ENDC}")
        return

    while True:
        try:
            user_input = input(f"{Colors.USER}You: {Colors.ENDC}").strip()
            if user_input.lower() in ("quit", "exit"):
                print(f"{Colors.INFO}Goodbye!{Colors.ENDC}")
                break
            if not user_input:
                continue

            response = chain.invoke({"user_input": user_input})
            print(f"{Colors.BOT}Bot: {response}{Colors.ENDC}")

        except ConnectionError as ce:
            print(f"{Colors.ERROR}Connection error: {ce}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.ERROR}Error: {e}{Colors.ENDC}")

if __name__ == "__main__":
    main_chat_loop()
