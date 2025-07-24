import logging
from rich.console import Console
from rich.panel import Panel
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from prompts import PACKAGE_ANALYSIS_PROMPT, RESULT_CHATBOT_PERSONA

# --- Initialize Logging & Console ---
log = logging.getLogger("package_ai")
console = Console()

# --- Initialize LLM ---
result_llm = ChatOpenAI(
    base_url="http://localhost:15207/v1",
    model_name="gpt-4o",
    temperature=0.7,
    api_key="not_needed",
)


def summarize_package_results(user_name, user_age, package_name, results):
    """
    Summarizes the results of a completed smart package.

    Args:
        user_name (str): The user's name.
        user_age (int): The user's age.
        package_name (str): The name of the smart package.
        results (list): A list of test results for the completed package.

    Returns:
        str: A comprehensive report of the user's package results.
    """
    log.info(f"--- Entering summarize_package_results for {user_name} ---")

    # Format the results for the prompt
    formatted_results = ""
    for result in results:
        formatted_results += f"### Test: {result['test_name']}\n\n"
        formatted_results += f"{result['result_text']}\n\n"

    # Generate the prompt for the final analysis
    prompt = PACKAGE_ANALYSIS_PROMPT.format(
        user_name=user_name,
        user_age=user_age,
        package_name=package_name,
        formatted_results=formatted_results,
    )

    # Define the system instruction
    system_instruction = RESULT_CHATBOT_PERSONA

    log.info("Generating in-depth package analysis...")

    # Log details before calling the LLM
    console.print(
        Panel(
            f"[cyan]System Instruction:[/cyan]\n{system_instruction}\n\n"
            f"[cyan]User/Task Prompt:[/cyan]\n{prompt}",
            title="AI Interaction Details (Package Summary Generation)",
            border_style="green",
            expand=False,
        )
    )

    # Get the AI response
    resp = result_llm.invoke(
        [SystemMessage(content=system_instruction), HumanMessage(content=prompt)]
    ).content.strip()

    console.print(
        Panel(
            f"[cyan]AI Response:[/cyan]\n{resp}",
            title="AI Response (Package Summary)",
            border_style="blue",
            expand=False,
        )
    )

    log.info(f"--- Exiting summarize_package_results ---")
    return resp
