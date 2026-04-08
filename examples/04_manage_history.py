import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from duckai import DuckAIClient, Model

async def main():
    client = DuckAIClient(model=Model.MISTRAL_SMALL, headless=True)
    await client.start()
    
    try:
        await client.chat("My favorite color is blue.")
        await client.chat("What is my favorite color?")
        
        print("History length:", len(client.history))
        
        print("\nChanging model and clearing history...")
        await client.change_model(Model.GPT5_MINI)
        
        print("History length after clear:", len(client.history))
        
        response = await client.chat("What is my favorite color?")
        print("\nResponse after clear:", response.content)
        
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())