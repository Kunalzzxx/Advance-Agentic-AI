import os
import json
from dotenv import load_dotenv
from groq import Groq

# Import your exact same tools!
from agent.basic_agent import get_current_time, calculate, get_weather, analyze_text
from agent.memory import save_memory, recall_memory

load_dotenv()

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Map function names to actual functions
AVAILABLE_FUNCTIONS = {
    "get_current_time": get_current_time,
    "calculate": calculate,
    "get_weather": get_weather,
    "analyze_text": analyze_text,
    "save_memory": save_memory,
    "recall_memory": recall_memory,
}

# Define tools for Llama 3
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Returns the current date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "Timezone like 'UTC', 'Asia/Tokyo'."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluates a mathematical expression safely.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression like '2 + 3 * 4'."}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Gets a simulated weather report for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name."},
                    "unit": {"type": "string", "description": "'celsius' or 'fahrenheit'."}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_text",
            "description": "Analyzes text and returns statistics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to analyze."}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Saves a piece of information to long-term memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Category (e.g., 'user_name')."},
                    "value": {"type": "string", "description": "The information to remember."}
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Searches long-term memory for a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Topic to search for."}
                },
                "required": ["query"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are a highly advanced AI assistant with long-term memory and local tools.

RULES:
1. For time/date -> use get_current_time
2. For math -> use calculate
3. For weather -> use get_weather
4. For text analysis -> use analyze_text
5. If user tells personal facts (e.g., "My name is John"), use `save_memory`.
6. If user asks about past info (e.g., "What is my name?"), use `recall_memory`.
7. NEVER guess personal details. Check memory first.
8. Keep responses concise.
"""

def chat_loop():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or "paste" in api_key:
        print(f"{RED}ERROR: GROQ_API_KEY not set in .env{RESET}")
        return

    client = Groq(api_key=api_key)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║   Advanced Agent (Llama 3 via Groq)     ║{RESET}")
    print(f"{BOLD}{CYAN}║   Features: Tools, Memory Management      ║{RESET}")
    print(f"{BOLD}{CYAN}╠══════════════════════════════════════════╣{RESET}")
    print(f"{BOLD}{CYAN}║   Type 'quit' to exit                   ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════╝{RESET}\n")

    while True:
        try:
            user_input = input(f"{BOLD}{GREEN}You: {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{YELLOW}Goodbye!{RESET}")
            break

        if not user_input: continue
        if user_input.lower() == "quit":
            print(f"{YELLOW}Goodbye!{RESET}")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            # Call Llama 3
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile", # Super fast and smart model
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )

            msg = response.choices[0].message
            
            # Check if model wants to call a tool
            while msg.tool_calls:
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    
                    if "memory" in func_name:
                        print(f"\n{MAGENTA}>> [MEMORY] {func_name}: {func_args}{RESET}")
                    else:
                        print(f"\n{YELLOW}>> Tool: {func_name}{RESET}")
                        print(f"{YELLOW}   Args: {func_args}{RESET}")

                    # Execute the actual Python function
                    func_to_call = AVAILABLE_FUNCTIONS[func_name]
                    result = func_to_call(**func_args)

                    if "memory" in func_name:
                        print(f"{MAGENTA}<< [MEMORY] {result}{RESET}\n")
                    else:
                        print(f"{GREEN}<< Result: {str(result)[:200]}{RESET}\n")

                    messages.append(msg)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })

                # Get next response from model after tool result
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    tools=TOOLS
                )
                msg = response.choices[0].message

            # If no tool calls, print final text
            if msg.content:
                print(f"{BOLD}{CYAN}Agent: {RESET}{msg.content}\n")
                messages.append({"role": "assistant", "content": msg.content})

        except Exception as e:
            print(f"{RED}Error: {str(e)}{RESET}\n")
            # Remove failed user message so it doesn't break the history
            messages.pop()

if __name__ == "__main__":
    chat_loop()