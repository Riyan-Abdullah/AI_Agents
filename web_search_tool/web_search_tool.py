from main import config
import os
from dotenv import load_dotenv
from agents import Agent, ModelSettings, Runner, function_tool
import requests



# Load API key
load_dotenv()
tavily_api_key = os.getenv("TAVILY_API_KEY")

@function_tool
def web_search(query: str) -> str:
    """Perform a web search using the Tavily API and return the results."""
    url = "https://api.tavily.com/search"   # ✅ fixed endpoint
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {tavily_api_key}"
    }
    search_depth = "basic"
    payload = {
        "query": query,
        "search_depth": search_depth
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# Define agent
agent = Agent(
    name="WebSearchAgent",
    instructions="You are a helpful assistant that can perform web searches to find information.",
    tools=[web_search],
    model_settings=ModelSettings(tool_choice="auto")
)

# Run agent
result = Runner.run_sync(
    agent,
    input=input("Enter your query: "),
    run_config=config
)

print(result.final_output)
