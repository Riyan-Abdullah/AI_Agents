from main import config
from agents import function_tool, Agent, Runner
import requests
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("WEATHER_API_KEY")

@function_tool
def get_weather(city : str) ->str:
    print(f"Fetching weather for {city}")
    response = requests.get(f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}")
    data = response.json()
    return f"The current weather in {city} is {data['current']['temp_c']} C with {data['current']['condition']['text']}. "

@function_tool
def Add(a: int, b: int) -> int:
    print(f"Adding {a} and {b}")
    return a + b

@function_tool
def Subtract(a: int, b: int) -> int:
    print(f"Subtracting {b} from {a}")
    return a - b

@function_tool
def Multiply(a: int, b: int) -> int:
    print(f"Multiplying {a} and {b}")
    return a * b

@function_tool
def Divide(a: int, b: int) -> float:
    print(f"Dividing {a} by {b}")
    if b == 0:
        return "Error: Division by zero is not allowed."
    return a / b



agent = Agent(
    name = "General Agent",
    instructions="You are helpful general agent . Your task is to help the user their queries",
    tools=[get_weather, Add, Subtract, Multiply, Divide]
)

result = Runner.run_sync(
    agent,
    input= input("Enter your query: "),
    run_config= config,

)

print(result.final_output)
