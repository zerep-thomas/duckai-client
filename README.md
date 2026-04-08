# Duck.ai Python Client

A fully asynchronous Python client for automating interactions with the Duck.ai chat interface.

This repository provides a programmatic wrapper around the Duck.ai web interface using Microsoft Playwright. It features browser stealth techniques, automated session handling, and a modular architecture to interact with multiple AI models (GPT-4o, Claude 3, Llama 3, etc.).

## Disclaimer

**STRICTLY FOR EDUCATIONAL AND RESEARCH PURPOSES.**

This software is a Proof of Concept (PoC) demonstrating advanced browser automation, headless UI interaction, and technical circumvention strategies.

Automated access to Duck.ai without utilizing an official API violates DuckDuckGo's Terms of Service. The author of this repository does not condone, encourage, or support the use of this software for heavy scraping, spam, denial of service, or any commercial application.

By utilizing this codebase, you assume all legal and technical responsibilities. The maintainers of this repository will not be held liable for any damages, IP bans, or account suspensions resulting from its use.

## Technical Capabilities

- **Fully Asynchronous Architecture**: Built on `asyncio` and `playwright.async_api` for high performance.
- **Multi-Model Support**: Dynamically switch between available models (GPT, Claude, Llama, Mistral).
- **Stealth Implementation**: Implements navigator overrides and context masking to mitigate standard bot-detection mechanisms.
- **Automated Challenge Resolution**: Includes logic to intercept and interact with UI challenges via external routing.
- **Pseudo-Streaming Support**: Yields character-by-character output for CLI integrations.
- **State Management**: Maintains conversation history locally and within the browser session.

## Prerequisites

Python 3.10 or higher is required.

## Installation

1. Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/duckai-client.git
cd duckai-client
```

2. Install the required Python packages:

```bash
pip install -r requirements.txt
```

3. Install Playwright browser binaries:

```bash
playwright install chromium
```

## Quick Start

The simplest way to use the client is via the `ask` utility function for one-shot queries.

```python
import asyncio
from duckai import ask, Model

async def main():
    response = await ask("Explain quantum computing in one sentence.", model=Model.GPT4O_MINI)
    print(response)

asyncio.run(main())
```

## Advanced Usage

For conversations that require maintaining context, use the `DuckAIClient` context manager.

```python
import asyncio
from duckai import DuckAIClient, Model

async def main():
    async with DuckAIClient(model=Model.CLAUDE_HAIKU, headless=True) as client:
        # First query
        response_1 = await client.chat("My name is John.")
        print(response_1.content)

        # Second query (context is maintained)
        response_2 = await client.chat("What is my name?")
        print(response_2.content)

asyncio.run(main())
```

_Note: Please refer to the `examples/` directory in this repository for more comprehensive usage patterns, including streaming and state management._

## API Reference

### `Model` (Class)

Constants defining available AI models.

- `Model.GPT5_MINI`
- `Model.GPT4O_MINI`
- `Model.CLAUDE_HAIKU`
- `Model.LLAMA4_SCOUT`
- `Model.MISTRAL_SMALL`
- `Model.GPT_OSS_120B`

### `DuckAIClient` (Class)

The core client handling browser lifecycle and interactions.

**Initialization:**

```python
client = DuckAIClient(model=Model.GPT4O_MINI, headless=True)
```

**Methods:**

- `await start()`: Initializes the Playwright context.
- `await close()`: Gracefully terminates the browser session.
- `await chat(prompt: str) -> ChatResponse`: Sends a prompt and returns the AI's response.
- `chat_stream(prompt: str) -> AsyncIterator[str]`: Yields response characters asynchronously.
- `await change_model(model: str)`: Switches the AI model and clears the current conversation.
- `clear_history()`: Wipes the local conversation history.

**Properties:**

- `history`: Returns a list of `Message` dataclasses representing the current conversation state.
