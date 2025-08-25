from agents import Agent
from connection import config

faq_responses = {
    "what is your name?": "I am FAQBot, your helpful assistant.",
    "who created you?": "I was created using the OpenAI Agent SDK.",
    "what can you do?": "I can answer simple predefined FAQ questions.",
    "how are you?": "I'm just code, but I'm running smoothly!",
    "bye": "Goodbye! Have a great day!"
}


agent = Agent(
    name="FAQBot",
    instructions="You are a helpful FAQ bot. Only answer from the predefined FAQ list."
)


def handle_message(message: str):
    normalized = message.lower().strip()
    return faq_responses.get(normalized, "Sorry, I don’t know the answer to that.")


if __name__ == "__main__":
    print("FAQBot is running. Type 'bye' to exit.")
    while True:
        user_input = input("You: ")
        response = handle_message(user_input)
        print("Bot:", response)
        if user_input.lower().strip() == "bye":
            break