from main import config
from agents import Agent, Runner, function_tool, ModelSettings

@function_tool
def  add(n1: int, n2: int) -> int:
    """Returns the sum of two numbers."""
    return n1 + n2

@function_tool
def subtract(n1: int, n2: int) -> int:
    """Returns the difference of two numbers."""
    return n1 - n2



agent = Agent(
    name = "AGENT",
    instructions = "You are a helpful assistant. Your task is to help the user with their queries.",
    tools=[add, subtract],
    model_settings=ModelSettings(tool_choice="auto",)
)

result = Runner.run_sync(
    agent,
    input= input("Enter your query:  "),
    run_config= config
)

print(result.final_output)
