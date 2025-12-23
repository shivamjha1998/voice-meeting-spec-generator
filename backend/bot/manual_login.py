import sys
import os
import time
from playwright.sync_api import sync_playwright

# Fix stealth import - handle both import styles
try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None
    print("⚠️ playwright-stealth not available")

# Ensure Python can find your backend folder
sys.path.append(os.getcwd())

def run_manual_login():
    # Use the EXACT same profile path as the bot
    user_data_dir = os.path.join(os.getcwd(), "google_profile")
    
    print(f"🚀 Opening browser with profile: {user_data_dir}")
    
    with sync_playwright() as p:
        # Match the bot's configuration to ensure session compatibility
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            user_agent=user_agent,
            args=[
                "--use-fake-ui-for-media-stream",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
            permissions=["microphone", "camera"],
            viewport={"width": 1280, "height": 720}
        )
        
        page = context.pages[0]

        # Apply stealth if available
        if stealth_sync:
            try:
                stealth_sync(page)
                print("✅ Stealth applied successfully")
            except Exception as e:
                print(f"⚠️ Stealth error (non-critical): {e}")
        
        # Override webdriver property
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Go to Google Login
        print("Navigating to Google Login...")
        page.goto("https://accounts.google.com/")
        
        print("\n" + "="*50)
        print("ACTION REQUIRED:")
        print("1. Log in to your Google account in the browser window.")
        print("2. Complete any 2FA prompts.")
        print("3. Wait until you see your Google account dashboard/inbox.")
        print("="*50 + "\n")
        
        input("Press [Enter] HERE after you have finished logging in to save the session...")
        context.close()
        print("✅ Session saved. Verifying persistence...")
        
    # VERIFICATION PHASE
    print("\n" + "="*50)
    print("VERIFYING SESSION PERSISTENCE...")
    time.sleep(2)
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            user_agent=user_agent,
            args=[
                "--use-fake-ui-for-media-stream",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
            permissions=["microphone", "camera"],
            viewport={"width": 1280, "height": 720}
        )
        
        page = context.pages[0]
        
        # Override webdriver property
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        print("Checking Google Account status...")
        page.goto("https://myaccount.google.com/")
        
        try:
            # Check for specific element indicating logged-in state
            # "Welcome" or "Home" or account info
            page.wait_for_selector("text=Welcome", timeout=5000)
            print("✅ SUCCESS! You are still logged in.")
        except:
            try:
                page.wait_for_selector('a[href*="logout"]', timeout=3000)
                print("✅ SUCCESS! Logout button found (implies logged in).")
            except:
                print("❌ FAILURE! Browser asked to sign in again or 'Welcome' not found.")
                print("Please check the browser window to see what happened.")
                input("Press [Enter] to close verification window...")
        
        context.close()

if __name__ == "__main__":
    run_manual_login()