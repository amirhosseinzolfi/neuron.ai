import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph, END
from colorama import Fore, Style, init
import json

# Initialize colorama for colorful logs
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=f"{Fore.CYAN}[%(asctime)s]{Style.RESET_ALL} %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)

# --------------------
# Step 1: Initialize LLM
# --------------------
llm = ChatOpenAI(
    base_url="http://141.98.210.15:15207/v1",
    model_name="gpt-5-nano",
    temperature=0.5,
    api_key="324"
)

# --------------------
# Step 2: Define User Profile Schema
# --------------------
class UserProfile(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    job: Optional[str] = None
    location: Optional[str] = None
    interests: Optional[List[str]] = []
    email: Optional[str] = None
    phone: Optional[str] = None

# --------------------
# Step 3: Prompt for JSON Output
# --------------------
profile_prompt = PromptTemplate(
    template="""
You are an intelligent profile extraction agent. 
Analyze the following user input. 
Return ONLY valid JSON with extracted profile fields (name, age, job, location, interests, email, phone).
If nothing relevant, return an empty JSON object.

User input: {text}
""",
    input_variables=["text"]
)

# --------------------
# Step 4: Build LangGraph Agent
# --------------------
class AgentState(Dict[str, Any]):
    profile: UserProfile
    new_input: str
    extracted: Optional[UserProfile] = None

# --- Nodes ---
def extract_info(state: AgentState):
    logging.info(f"{Fore.YELLOW}Extracting info from input:{Style.RESET_ALL} {state['new_input']}")
    response = llm.invoke(profile_prompt.format(text=state["new_input"]))
    try:
        data = json.loads(response.content)
        extracted = UserProfile(**data)
        logging.info(f"{Fore.GREEN}Extracted Data:{Style.RESET_ALL} {data}")
        return {"extracted": extracted}
    except Exception as e:
        logging.error(f"{Fore.RED}Failed to parse LLM output:{Style.RESET_ALL} {response.content}")
        return {"extracted": None}

def update_profile(state: AgentState):
    logging.info(f"{Fore.BLUE}Updating profile with new data...{Style.RESET_ALL}")
    profile: UserProfile = state["profile"]
    new_data: Optional[UserProfile] = state.get("extracted")
    if not new_data:
        logging.warning("No new data extracted, profile unchanged.")
        return {"profile": profile}
    
    # Merge only new non-empty fields
    updated = profile.model_dump()
    for k, v in new_data.model_dump().items():
        if v:
            updated[k] = v
            logging.info(f"{Fore.MAGENTA}Updated field:{Style.RESET_ALL} {k} → {v}")

    new_profile = UserProfile(**updated)
    logging.info(f"{Fore.GREEN}Current Profile State:{Style.RESET_ALL} {new_profile.model_dump()}")
    return {"profile": new_profile}

# --- Build Graph ---
graph = StateGraph(AgentState)

graph.add_node("extract_info", extract_info)
graph.add_node("update_profile", update_profile)

graph.set_entry_point("extract_info")
graph.add_edge("extract_info", "update_profile")
graph.add_edge("update_profile", END)

app = graph.compile()

# --------------------
# Step 5: Run Agent Demo
# --------------------
if __name__ == "__main__":
    profile = UserProfile()
    inputs = [
        "Hi, my name is Sarah and I’m 27.",
        "I work as a software engineer in Berlin.",
        "My email is sarah.doe@gmail.com",
        "By the way, I like hiking and photography.",
        "im programmer and graphist",
        "i love coffee"
    ]

    for text in inputs:
        logging.info(f"{Fore.CYAN}Processing new input...{Style.RESET_ALL}")
        state = {"profile": profile, "new_input": text}
        result = app.invoke(state)
        profile = result.get("profile", profile)

    logging.info(f"{Fore.CYAN}Final User Profile:{Style.RESET_ALL}\n{profile.model_dump_json(indent=2)}")
