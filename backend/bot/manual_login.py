import sys
import os
from playwright.sync_api import sync_playwright

# Ensure Python can find your backend folder
sys.path.append(os.getcwd())

def run_manual_login():
    # Use the EXACT same profile path as the bot
    user_data_dir = os.path.join(os.getcwd(), "google_profile")
    
    print(f"🚀 Opening browser with profile: {user_data_dir}")
    
    with sync_playwright() as p:
        # Match the bot's configuration to ensure session compatibility
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            user_agent=user_agent,
            args=[
                "--use-fake-ui-for-media-stream",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
            ],
            ignore_default_args=["--enable-automation"],
            permissions=["microphone", "camera"],
            viewport={"width": 1280, "height": 720}
        )
        
        page = context.pages[0]
        
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
        print("✅ Session saved successfully. You can now run the bot normally.")

if __name__ == "__main__":
    run_manual_login()