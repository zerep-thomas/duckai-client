"""
chatbot.py — Interactive CLI Chatbot using DuckAIClient
Demonstrates how to use the streaming feature of the duckai.py module.
"""

import asyncio
import sys
from duckai import DuckAIClient, Model

# ANSI escape codes for colored terminal output
class Colors:
    USER = '\033[94m'      # Blue
    BOT = '\033[92m'       # Green
    SYSTEM = '\033[93m'    # Yellow
    RESET = '\033[0m'      # Reset to default

async def main() -> None:
    # 1. Choose the model you want to use
    selected_model = Model.CLAUDE_HAIKU
    
    print(f"{Colors.SYSTEM}--- Duck.ai Interactive Chat ---{Colors.RESET}")
    print(f"{Colors.SYSTEM}Model: {Model.label(selected_model)}{Colors.RESET}")
    print(f"{Colors.SYSTEM}Commands: 'quit' to exit, 'clear' to wipe history.{Colors.RESET}")
    print(f"{Colors.SYSTEM}Initializing browser... Please wait.{Colors.RESET}\n")

    # 2. Initialize the client within a context manager
    try:
        async with DuckAIClient(model=selected_model, headless=True) as client:
            print(f"{Colors.SYSTEM}Ready! Type your message.{Colors.RESET}\n")
            
            # 3. Main conversation loop
            while True:
                # Use asyncio.to_thread to prevent input() from blocking the async event loop
                user_input = await asyncio.to_thread(input, f"{Colors.USER}You: {Colors.RESET}")
                
                # Clean the input
                user_input = user_input.strip()
                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() in ['quit', 'exit']:
                    print(f"{Colors.SYSTEM}Goodbye!{Colors.RESET}")
                    break
                
                if user_input.lower() == 'clear':
                    client.clear_history()
                    print(f"{Colors.SYSTEM}[History cleared]{Colors.RESET}\n")
                    continue

                # Print the bot prefix
                print(f"{Colors.BOT}Bot: {Colors.RESET}", end="", flush=True)

                # 4. Stream the response
                try:
                    async for char in client.chat_stream(user_input):
                        sys.stdout.write(char)
                        sys.stdout.flush()
                except Exception as e:
                    print(f"\n{Colors.SYSTEM}[Error during generation: {e}]{Colors.RESET}")
                
                # Print a final newline when the stream is done
                print("\n")

    except KeyboardInterrupt:
        # Handle CTRL+C gracefully
        print(f"\n{Colors.SYSTEM}Process interrupted by user. Exiting...{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.SYSTEM}Fatal error: {e}{Colors.RESET}")

if __name__ == "__main__":
    # Standard boilerplate to run the main async function
    asyncio.run(main())