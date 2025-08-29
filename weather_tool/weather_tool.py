from agents import Agent , Runner, function_tool
from main import config
import os 
from dotenv import load_dotenv
import requests



load_dotenv()
weather_api_key = os.getenv("WEATHER_API_KEY")

@function_tool
def get_weather(city : str) ->str:
    response = requests.get(f"http://api.weatherapi.com/v1/current.json?key={weather_api_key}&q={city}")
    data = response.json()
    return f"The current weather in {city} is {data['current']['temp_c']} C with {data['current']['condition']['text']}. "


weather_agent = Agent(
    name = "Weather_Agent",
    instructions="You are a helpful weather assistant. Use the get_weather tool to fetch current weather information for a given city.",
    tools=[get_weather]
    
)

result = Runner.run_sync(
    weather_agent,
    input=input("Enter your query: "),
    run_config= config,

)

print(result.final_output)