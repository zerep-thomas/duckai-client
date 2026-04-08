import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from duckai import DuckAIClient, Model

async def main():
    # Using context manager ensures the browser is closed properly
    async with DuckAIClient(model=Model.GPT4O_MINI, headless=True) as client:
        print("User: Hello! Who are you?")
        response = await client.chat("Hello! Who are you?")
        print(f"Bot ({response.model}): {response.content}\n")

        print("User: Can you summarize my previous message?")
        response2 = await client.chat("Can you summarize my previous message?")
        print(f"Bot: {response2.content}")

if __name__ == "__main__":
    asyncio.run(main())