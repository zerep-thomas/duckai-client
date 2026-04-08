import asyncio
import sys
import os

# Add parent directory to path to import duckai
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from duckai import ask, Model

async def main():
    print("Sending request...")
    # One-shot request using the ask utility
    response = await ask("Write a short poem about coding.", model=Model.CLAUDE_HAIKU)
    print("\nResponse:\n")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())