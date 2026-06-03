"""
Basic Agentic AI built with Google ADK.
Includes: Time, Calculator, Weather, Text Analysis, and Memory Management.
"""

from google.adk.agents import LlmAgent
import datetime
import json
import math
import random
from agent.memory import save_memory, recall_memory

# ──────────────────────────────────────────────
#  TOOL 1: Get current date/time
# ──────────────────────────────────────────────
def get_current_time(timezone: str = "UTC") -> str:
    """Returns the current date and time.

    Args:
        timezone: A timezone string like 'UTC', 'US/Eastern', 'Asia/Tokyo'.

    Returns:
        A formatted string with the current date and time.
    """
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        if timezone.upper() != "UTC":
            try:
                import zoneinfo
                tz = zoneinfo.ZoneInfo(timezone)
                now = now.astimezone(tz)
            except Exception:
                return f"Could not find timezone '{timezone}'. Using UTC: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        return now.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception as e:
        return f"Error getting time: {str(e)}"


# ──────────────────────────────────────────────
#  TOOL 2: Calculator
# ──────────────────────────────────────────────
def calculate(expression: str) -> str:
    """Evaluates a mathematical expression safely.

    Args:
        expression: A math expression like '2 + 3 * 4', 'sqrt(16)'.

    Returns:
        The result of the calculation as a string.
    """
    safe_dict = {
        "abs": abs, "round": round, "min": min, "max": max,
        "pow": pow, "sqrt": math.sqrt, "log": math.log,
        "log10": math.log10, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "pi": math.pi, "e": math.e,
        "ceil": math.ceil, "floor": math.floor,
    }
    blocked = ["import", "exec", "eval", "open", "file", "__", "class", "def", "lambda", ";"]
    for b in blocked:
        if b in expression.lower():
            return f"Error: Unsafe expression detected."
    try:
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return str(result)
    except ZeroDivisionError:
        return "Error: Division by zero."
    except Exception as e:
        return f"Error: {str(e)}"


# ──────────────────────────────────────────────
#  TOOL 3: Simulated weather
# ──────────────────────────────────────────────
def get_weather(city: str, unit: str = "celsius") -> str:
    """Gets a simulated weather report for a city.

    Args:
        city: The name of the city.
        unit: 'celsius' or 'fahrenheit'.

    Returns:
        A weather report as JSON string.
    """
    seed = hash(city.lower().strip())
    rng = random.Random(seed)
    temp_c = rng.randint(-5, 40)
    conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Stormy", "Snowy", "Foggy"]
    condition = rng.choice(conditions)
    humidity = rng.randint(20, 95)
    if unit.lower().startswith("f"):
        temp = (temp_c * 9/5) + 32
        temp_str = f"{temp:.1f}°F"
    else:
        temp_str = f"{temp_c}°C"
    report = {
        "city": city.title(),
        "temperature": temp_str,
        "condition": condition,
        "humidity": f"{humidity}%",
        "note": "Simulated data"
    }
    return json.dumps(report, indent=2)


# ──────────────────────────────────────────────
#  TOOL 4: Text analysis
# ──────────────────────────────────────────────
def analyze_text(text: str) -> str:
    """Analyzes text and returns statistics.

    Args:
        text: The text to analyze.

    Returns:
        JSON with word count, character count, sentence count.
    """
    words = text.split()
    sentences = [s for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    avg_word_len = sum(len(w.strip(".,!?;:'\"")) for w in words) / max(len(words), 1)
    stats = {
        "characters": len(text),
        "words": len(words),
        "sentences": len(sentences),
        "avg_word_length": round(avg_word_len, 2),
    }
    return json.dumps(stats, indent=2)


# ──────────────────────────────────────────────
#  AGENT DEFINITION
# ──────────────────────────────────────────────
def create_agent() -> LlmAgent:
    agent = LlmAgent(
        name="advanced_assistant",
        
        # Using 1.5-flash to avoid 2.0 quota limits
        model="gemini-pro",
        
        instruction="""You are a highly advanced AI assistant with local tools and long-term memory.

BEHAVIOR RULES:
1. For time/date questions -> use get_current_time
2. For math questions -> use calculate
3. For weather questions -> use get_weather
4. For text analysis -> use analyze_text

MEMORY MANAGEMENT RULES (CRITICAL):
5. If the user tells you personal facts (e.g., "My name is John", "I love python"), YOU MUST use `save_memory` to store it.
6. If the user asks about something they mentioned before (e.g., "What is my name?", "Do you remember my hobby?"), YOU MUST use `recall_memory` first.
7. NEVER guess a user's personal detail. Always check recall_memory first.
8. Keep responses concise but complete.
""",
        
        # ONLY Python functions here. No strings.
        tools=[
            get_current_time,
            calculate,
            get_weather,
            analyze_text,
            save_memory,
            recall_memory
        ],
    )
    return agent