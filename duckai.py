"""
duckai.py — Python Client for Duck.ai
Uses Playwright to drive duck.ai as a chat API.
"""

import asyncio
import base64
import httpx
import json
import re
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Tuple, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


# ─────────────────────────────────────────────
# AVAILABLE MODELS
# ─────────────────────────────────────────────

class Model:
    GPT5_MINI       = "gpt-5-mini"
    GPT4O_MINI      = "gpt-4o-mini"
    GPT_OSS_120B    = "tinfoil/gpt-oss-120b"
    LLAMA4_SCOUT    = "meta-llama/Llama-4-Scout-17B-16E-Instruct"
    CLAUDE_HAIKU    = "claude-haiku-4-5"
    MISTRAL_SMALL   = "mistralai/Mistral-Small-24B-Instruct-2501"

    _LABELS = {
        GPT5_MINI:    "GPT-5 mini",
        GPT4O_MINI:   "GPT-4o mini",
        GPT_OSS_120B: "gpt-oss 120B",
        LLAMA4_SCOUT: "Llama 4 Scout",
        CLAUDE_HAIKU: "Claude Haiku 4.5",
        MISTRAL_SMALL:"Mistral Small 3",
    }

    @classmethod
    def label(cls, model_value: str) -> str:
        """Returns the display label for a given model value."""
        return cls._LABELS.get(model_value, model_value)

    @classmethod
    def all(cls) -> Dict[str, str]:
        """Returns a mapping of {value: label} for all available models."""
        return dict(cls._LABELS)


# ─────────────────────────────────────────────
# DATA TYPES
# ─────────────────────────────────────────────

@dataclass
class Message:
    role: str          # "user" or "assistant"
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    history: List[Message] = field(default_factory=list)


# ─────────────────────────────────────────────
# CAPTCHA SOLVER (Internal)
# ─────────────────────────────────────────────

async def _solve_captcha_with_duckduckgo(screenshot_bytes: bytes) -> List[Tuple[int, int]]:
    """Requests DuckDuckGo's Chat API to solve the CAPTCHA grid."""
    b64 = base64.b64encode(screenshot_bytes).decode()
    async with httpx.AsyncClient() as client:
        status_resp = await client.get(
            "https://duckduckgo.com/duckchat/v1/status",
            headers={"x-vqd-accept": "1"},
        )
        vqd_token = status_resp.headers.get("x-vqd-4", "")
        payload = {
            "model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": (
                        "This is a 3x3 CAPTCHA grid. "
                        "Which cells (row, col) contain a duck? "
                        "Rows and columns are 0-indexed from top-left. "
                        "Reply ONLY with JSON like: [[0,2],[1,1]]"
                    )},
                ],
            }],
        }
        resp = await client.post(
            "https://duckduckgo.com/duckchat/v1/chat",
            headers={"Content-Type": "application/json", "x-vqd-4": vqd_token},
            json=payload,
            timeout=30,
        )

    full_text = ""
    for line in resp.text.splitlines():
        if line.startswith("data: ") and line != "data: [DONE]":
            try:
                chunk = json.loads(line[6:])
                full_text += chunk.get("message", "")
            except Exception:
                pass

    match = re.search(r"\[\s*\[.*?\]\s*\]", full_text, re.DOTALL)
    return json.loads(match.group()) if match else []


async def _handle_captcha(page: Page) -> None:
    """Detects and attempts to solve a CAPTCHA challenge on the page."""
    try:
        captcha_box = page.locator("[class*='captcha'], [class*='challenge'], [class*='modal']").first
        screenshot = await captcha_box.screenshot()
        positions = await _solve_captcha_with_duckduckgo(screenshot)
        if not positions:
            return
            
        images = await page.locator(
            "[class*='captcha'] img, [class*='challenge'] img, [class*='modal'] img"
        ).all()
        
        for row, col in positions:
            idx = row * 3 + col
            if idx < len(images):
                await images[idx].click()
                await page.wait_for_timeout(400)
                
        await page.wait_for_timeout(500)
        
        # Multi-language submit selectors are kept to maintain cross-locale compatibility
        submit = page.locator("button:has-text('Envoyer'), button:has-text('Submit'), button:has-text('Verify')")
        if await submit.is_visible(timeout=3000):
            await submit.click()
            await page.wait_for_timeout(2000)
    except Exception:
        pass


# ─────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────

async def _dismiss_welcome(page: Page) -> None:
    """Attempts to dismiss the welcome/onboarding modal dialogs."""
    # Multi-language selectors are kept to support rendering in French or English locales
    selectors = [
        "button:has-text('Got it')",
        "button:has-text('Accept')",
        "button:has-text('Accepter')",
        "button:has-text('Continue')",
        "button:has-text('Continuer')",
        "button:has-text('Start chatting')",
        "button:has-text('Commencer')",
        "[data-testid='onboarding-dismiss']",
        "[class*='welcome'] button",
        "[class*='onboarding'] button",
    ]

    async def try_click(sel: str) -> bool:
        try:
            btn = page.locator(sel).first
            await btn.wait_for(state="visible", timeout=3000)
            await btn.click()
            return True
        except Exception:
            return False

    tasks = [asyncio.create_task(try_click(s)) for s in selectors]
    for coro in asyncio.as_completed(tasks):
        if await coro:
            for t in tasks:
                t.cancel()
            await page.wait_for_timeout(200)
            return
            
    for t in tasks:
        t.cancel()


async def _select_model(page: Page, model_value: str) -> None:
    """Selects the specified AI model from the UI dropdown."""
    await page.click('[data-testid="model-select-button"]')
    await page.wait_for_timeout(500)
    
    await page.evaluate("""(modelValue) => {
        const input = [...document.querySelectorAll('input[name="model"]')]
            .find(el => el.value === modelValue);
        if (!input) return;
        
        const label = document.querySelector(`label[for="${input.id}"]`);
        if (label) { label.click(); return; }
        
        const parent = input.closest('li, label');
        if (parent) { parent.click(); return; }
        
        input.click();
    }""", model_value)
    
    await page.wait_for_timeout(400)
    
    confirm = page.locator("button:has-text('Démarrer un nouveau chat'), button:has-text('Start new chat')")
    try:
        await confirm.wait_for(state="visible", timeout=2000)
        await confirm.click()
        await page.wait_for_timeout(400)
    except Exception:
        pass


async def _extract_last_response(page: Page) -> str:
    """Extracts the final text response from the chat UI."""
    await page.wait_for_selector(
        "button svg path[d*='M8 .5a.75.75 0 0 1 .75.75v8.264']",
        timeout=120_000,
        state="visible",
    )
    await page.wait_for_timeout(200)
    
    return await page.evaluate("""() => {
        const msgs = [...document.querySelectorAll('[data-activeresponse]')];
        if (msgs.length === 0) return "";
        const last = msgs[msgs.length - 1];
        
        const headingEl = last.querySelector('[id*="heading-"]');
        const headingText = headingEl ? headingEl.innerText.trim() : "";
        const fullText = last.innerText.trim();
        
        return (headingText && fullText.startsWith(headingText))
            ? fullText.slice(headingText.length).trim()
            : fullText;
    }""")


def _browser_args() -> List[str]:
    """Returns the default launch arguments for Chromium."""
    return [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1366,768",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
    ]


def _context_options() -> Dict:
    """Returns the context options for stealth browsing."""
    return dict(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1366, "height": 768},
        locale="fr-FR",  # Maintained as original to match selectors
        timezone_id="Europe/Paris",
        java_script_enabled=True,
        bypass_csp=True,
        extra_http_headers={
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        },
    )


_STEALTH_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = { runtime: {}, loadTimes: () => {}, csi: () => {} };
    Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR','fr'] });
    Object.defineProperty(screen, 'width',  { get: () => 1366 });
    Object.defineProperty(screen, 'height', { get: () => 768  });
"""


# ─────────────────────────────────────────────
# MAIN CLIENT
# ─────────────────────────────────────────────

class DuckAIClient:
    """
    Asynchronous client for the Duck.ai API.

    Recommended usage — via context manager:

        async with DuckAIClient(model=Model.CLAUDE_HAIKU) as client:
            response = await client.chat("Hello there!")
            print(response.content)

    Manual usage:

        client = DuckAIClient()
        await client.start()
        response = await client.chat("Hello there!")
        await client.close()
    """

    def __init__(
        self,
        model: str = Model.GPT4O_MINI,
        headless: bool = True,
    ):
        self.model = model
        self.headless = headless

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._history: List[Message] = []
        self._started = False

    # ── Lifecycle ──────────────────────────────

    async def start(self) -> None:
        """Initializes the browser and opens duck.ai. Must be called before chat()."""
        if self._started:
            return
            
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=_browser_args(),
            chromium_sandbox=False,
        )
        self._context = await self._browser.new_context(**_context_options())
        await self._context.add_init_script(_STEALTH_SCRIPT)
        self._page = await self._context.new_page()

        await self._page.goto("https://duck.ai", wait_until="load")
        await _dismiss_welcome(self._page)
        await _select_model(self._page, self.model)
        
        self._started = True

    async def close(self) -> None:
        """Gracefully closes the browser and Playwright context."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
            
        self._started = False

    # ── Context Manager ────────────────────────

    async def __aenter__(self) -> "DuckAIClient":
        await self.start()
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    # ── Public API ─────────────────────────────

    async def chat(self, prompt: str) -> ChatResponse:
        """
        Sends a message and returns the response.

        Args:
            prompt: The text prompt to send.

        Returns:
            ChatResponse containing the content, the model used, and chat history.
            
        Raises:
            RuntimeError: If the client was not started.
        """
        if not self._started:
            raise RuntimeError("Client is not started. Call start() or use 'async with'.")

        self._history.append(Message(role="user", content=prompt))

        textarea = self._page.locator("textarea, input[type='text']").first
        await textarea.wait_for(state="visible", timeout=10_000)
        await textarea.click()
        await self._page.wait_for_timeout(100)
        await textarea.type(prompt, delay=40)
        await self._page.wait_for_timeout(200)
        await textarea.press("Enter")

        # CAPTCHA verification
        await self._page.wait_for_timeout(1000)
        captcha_detected = await self._page.evaluate("""() => {
            const t = document.body.innerText.toLowerCase();
            return t.includes('captcha') || t.includes('bot');
        }""")
        if captcha_detected:
            await _handle_captcha(self._page)

        content = await _extract_last_response(self._page)
        self._history.append(Message(role="assistant", content=content))

        return ChatResponse(
            content=content,
            model=self.model,
            history=list(self._history),
        )

    async def chat_stream(self, prompt: str) -> AsyncIterator[str]:
        """
        Sends a message and yields characters one by one (pseudo-streaming).
        Useful for displaying the response progressively in a terminal.

        Args:
            prompt: The text prompt to send.

        Yields:
            Characters of the response as they become available.
        """
        response = await self.chat(prompt)
        for char in response.content:
            yield char
            await asyncio.sleep(0.008)

    def clear_history(self) -> None:
        """Clears the client-side conversation history."""
        self._history.clear()

    @property
    def history(self) -> List[Message]:
        """Returns a copy of the current conversation history."""
        return list(self._history)

    async def change_model(self, model: str) -> None:
        """
        Switches the active model during a session.

        Args:
            model: The model identifier (use Model.* constants).
            
        Raises:
            RuntimeError: If the client was not started.
        """
        if not self._started:
            raise RuntimeError("Client is not started. Call start() or use 'async with'.")
            
        self.model = model
        await _select_model(self._page, model)
        self.clear_history()


# ─────────────────────────────────────────────
# UTILITY FUNCTION: One-shot call
# ─────────────────────────────────────────────

async def ask(prompt: str, model: str = Model.GPT4O_MINI) -> str:
    """
    Shortcut to ask a single question without manually managing the client lifecycle.

    Args:
        prompt: The question or prompt to send.
        model:  The model to use (default: GPT-4o mini).

    Returns:
        The text response generated by the AI.

    Example:

        answer = await ask("What is the capital of France?")
        print(answer)
    """
    async with DuckAIClient(model=model) as client:
        response = await client.chat(prompt)
        return response.content