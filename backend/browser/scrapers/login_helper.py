"""Script to login to LinkedIn/Indeed manually and persist cookies for the scraper."""

import asyncio
import os
import sys

# Add backend directory to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from playwright.async_api import async_playwright
from browser.session_manager import SessionManager
from browser.browser_config import BrowserConfig

async def manual_login(site: str):
    site = site.lower()
    if site not in ["linkedin", "indeed"]:
        print("Invalid site! Choose 'linkedin' or 'indeed'.")
        return

    session_id = site
    config = BrowserConfig(headless=False)  # Launch visible browser
    
    print(f"\n========================================================")
    print(f"Opening visible browser to log in to {site.capitalize()}...")
    print(f"Please log in, complete any verification (2FA/CAPTCHA), and verify you are on the home screen.")
    print(f"Once logged in, return to this terminal and press ENTER to save your session.")
    print(f"========================================================\n")

    async with async_playwright() as p:
        # Launch headed chromium browser
        browser = await p.chromium.launch(headless=False)
        session_manager = SessionManager(session_dir="sessions")
        
        # Load existing cookies if present
        context = await session_manager.get_or_create_context(session_id, browser, config)
        page = await context.new_page()
        
        if site == "linkedin":
            await page.goto("https://www.linkedin.com/login")
        else:
            await page.goto("https://secure.indeed.com/account/login")
            
        # Wait for user to press enter in the terminal
        await asyncio.get_event_loop().run_in_executor(None, input, "Press ENTER here after you have successfully logged in...")
        
        # Save state
        await session_manager.save_session_state(session_id)
        await context.close()
        await browser.close()
        
    print(f"\n[Success] Cookies and session state for '{site}' saved successfully!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python browser/scrapers/login_helper.py <linkedin|indeed>")
        sys.exit(1)
        
    target_site = sys.argv[1]
    asyncio.run(manual_login(target_site))
