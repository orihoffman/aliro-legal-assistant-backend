from playwright.async_api import async_playwright
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access the variables
google_password = os.getenv("GOOGLE_PASSWORD")
google_email = os.getenv("GOOGLE_EMAIL")


class ConversationSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):
        """Start the conversation session by launching the browser and navigating to the chat page."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()  # Set headless=False for debugging
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36",
            locale="en-US",
            viewport={"width": 1280, "height": 800}
        )
        self.page = await self.context.new_page()

        await self.page.goto("https://notebooklm.google.com/notebook/fef71e75-6992-48b7-8912-6955b19c99d9", wait_until="domcontentloaded")

        title = await self.page.title()
        print(f"[Debug] Page title: {title}")

        if "Sign in" in title or "login" in title.lower():
            print("Login required. Attempting login...")

            try:
                await self._handle_login()

                # After login, wait for the input field to ensure it's ready
                await self.page.wait_for_selector(".message-container input, .message-container textarea", timeout=60000)
                print(f"Session {self.session_id} logged in and ready.")

            except Exception as e:
                print(f"❌ Login failed: {e}")
                await self.stop()
        else:
            try:
                # Already authenticated
                await self.page.wait_for_selector(".message-container input, .message-container textarea", timeout=60000)
                print(f"Session {self.session_id} is already authenticated and ready.")
            except Exception as e:
                print(f"❌ Error reaching input field: {e}")
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

                await asyncio.sleep(1)

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

    async def _handle_login(self):
        try:
            # Locate and fill email
            email_input = await self.page.query_selector(
                "input[type='email'], input[name='identifier'], input[autocomplete='username']"
            )
            if not email_input:
                raise Exception("Could not find email input field.")

            await email_input.fill(google_email)
            print("✅ Filled email")
            next_button = await self.page.query_selector("button:has-text('Next')")
            if not next_button:
                raise Exception("Could not find 'Next' button after email entry.")
            await next_button.click()
            print("✅ Clicked 'Next' after email")

            # Locate and fill password
            await self.page.wait_for_selector("input[type='password']", timeout=15000)
            password_input = await self.page.query_selector("input[type='password']")
            if not password_input:
                raise Exception("Could not find password input field.")

            await password_input.fill(google_password)
            print("✅ Filled password")
            next_button = await self.page.query_selector("button:has-text('Next')")
            if not next_button:
                raise Exception("Could not find 'Next' button after password entry.")
            await next_button.click()
            print("✅ Clicked 'Next' after password")

            # Wait until conversation input is available
            await self.page.wait_for_selector(".message-container input, .message-container textarea", timeout=60000)
            print("✅ Logged in successfully")

        except Exception as e:
            raise Exception(f"Login sequence failed: {e}")


if __name__ == "__main__":
    import asyncio

    async def save_auth():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://notebooklm.google.com/")
            print("Login manually and press ENTER here once done...")
            input()
            await browser.close()

    asyncio.run(save_auth())