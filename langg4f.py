from g4f.integration.langchain import ChatAI
import g4f.debug

# Enable debugging logs
g4f.debug.logging = True

llm = ChatAI(
    model="gemini-1.5-flash",
    api_key="11"  # Optionally add your API key here
)

messages = [
    {"role": "user", "content": "2 🦜 2"},
    {"role": "assistant", "content": "4 🦜"},
    {"role": "user", "content": "2 🦜 3"},
    {"role": "assistant", "content": "5 🦜"},
    {"role": "user", "content": "3 🦜 4"},
]

response = llm.invoke(messages)
assert(response.content == "7 🦜")