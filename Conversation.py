from playwright.async_api import async_playwright
import asyncio
import os


class ConversationSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.auth_path = "auth_state.json"

    async def start(self):
        """Start the conversation session by launching the browser and navigating to the chat page."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()

        # Load saved login state if available
        if os.path.exists(self.auth_path):
            self.context = await self.browser.new_context(storage_state=self.auth_path)
        else:
            self.context = await self.browser.new_context()

        self.page = await self.context.new_page()
        await self.page.goto("https://notebooklm.google.com/notebook/fef71e75-6992-48b7-8912-6955b19c99d9")

        try:
            # Wait for either input OR login
            await self.page.wait_for_selector(
                ".message-container input, .message-container textarea, input[type='email']", timeout=30000
            )

            # Detect if login is needed
            if await self.page.query_selector("input[type='email']"):
                raise Exception("Login required. Session expired or not authenticated.")

            print(f"Session {self.session_id} is ready to chat.")

            # Save login state (only if newly logged in)
            await self.context.storage_state(path=self.auth_path)

        except Exception as e:
            print(f"Error initializing session {self.session_id}: {e}")
            await self.stop()

    async def send_and_receive(self, message: str):
        """Send a message and stream the assistant's response."""
        try:
            input_box = await self.page.query_selector(".message-container input, .message-container textarea")
            if not input_box:
                raise Exception("Input field not found — session may have expired or not authenticated.")

            await input_box.fill(message)
            await input_box.press("Enter")

            await self._wait_for_new_message()

            # Stream assistant message as it changes
            last_value = ""
            unchanged_count = 0
            response_text = ""

            while True:
                elements = await self.page.query_selector_all(".to-user-message-card-content .message-text-content")
                if not elements:
                    continue

                current_value = (await elements[-1].inner_text()).strip()

                if current_value != last_value:
                    delta = current_value[len(last_value):]
                    response_text += delta
                    last_value = current_value
                    unchanged_count = 0
                else:
                    unchanged_count += 1

                if unchanged_count >= 5:
                    break

                await asyncio.sleep(0.75)

            return response_text

        except Exception as e:
            print(f"Error during message exchange in session {self.session_id}: {e}")
            return "❌ Session error: likely expired or not authenticated."

    async def _wait_for_new_message(self):
        """Wait until a new assistant message element appears with non-empty text."""
        for _ in range(200):  # ~40 seconds
            elements = await self.page.query_selector_all(".to-user-message-card-content .message-text-content")
            if elements:
                content = await elements[-1].inner_text()
                if content.strip():
                    return
            await asyncio.sleep(0.2)

    async def stop(self):
        """Clean up browser resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print(f"Session {self.session_id} has been stopped.")
