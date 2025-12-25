class AudioConfigurator:
    def __init__(self, bot):
        self.bot = bot
        self.page = bot.page

    def configure_devices(self):
        """Selects BlackHole devices for Mic and Speakers with improved overlay handling"""
        try:
            print("🔧 Opening audio settings...")
            
            # 1. Open More Options -> Settings
            self.page.get_by_label("More options").click()
            self.bot._human_delay(1, 2)
            
            # Try to find 'Settings' specifically in the menu overlay
            settings_button = self.page.locator('span:has-text("Settings"), [role="menuitem"]:has-text("Settings")').first
            settings_button.click()
            
            # 2. Wait for Settings Dialog
            self.page.wait_for_selector('div[role="dialog"]', timeout=5000)
            self.bot._human_delay(1, 1.5)

            # 3. Ensure Audio tab is active
            audio_tab = self.page.get_by_role("tab", name="Audio")
            if audio_tab.is_visible():
                audio_tab.click()
                self.bot._human_delay(0.5, 1)

            # 4. Configure Microphone and Speaker
            configs = [
                {"label": "Microphone", "target": "BlackHole 16ch"},
                {"label": "Speaker", "target": "BlackHole 2ch"}
            ]

            for config in configs:
                label = config["label"]
                target = config["target"]
                print(f"\n🎯 Configuring {label} to {target}...")

                # Find the dropdown trigger for Mic or Speaker
                # Google Meet uses a div with aria-haspopup="menu" and an aria-label
                dropdown = self.page.locator(f'div[role="combobox"][aria-label*="{label}"], div[aria-haspopup="menu"][aria-label*="{label}"]').first
                
                if dropdown.is_visible():
                    dropdown.click(force=True)
                    # Temporary debug line to see all available options
                    # print("Available options:", self.page.locator('[role="option"]').all_inner_texts())
                    self.bot._human_delay(1, 1.5)

                    # STRATEGY: Look for the option in the entire page (overlays are often at the root)
                    # We look for role="option" or role="menuitem" that contains our text
                    option_selector = f'div[role="option"] >> text="{target}"'
                    
                    # Fallback list of selectors if the primary one fails
                    fallbacks = [
                        f'div[role="option"]:has-text("{target}")',
                        f'span:has-text("{target}")',
                        f'[role="listbox"] >> text="{target}"'
                    ]

                    found = False
                    for selector in [option_selector] + fallbacks:
                        try:
                            option = self.page.locator(selector).first
                            if option.is_visible(timeout=2000):
                                print(f"  ✅ Found option with selector: {selector}")
                                option.click(force=True)
                                found = True
                                break
                        except:
                            continue

                    if not found:
                        print(f"  ❌ Could not find {target} in the menu. Pressing Escape.")
                        self.page.keyboard.press("Escape")
                    
                    self.bot._human_delay(0.5, 1)
                else:
                    print(f"  ❌ {label} dropdown not found.")

            # 5. Close settings
            self.page.keyboard.press("Escape")
            print("\n✅ Audio configuration attempt finished.")

        except Exception as e:
            print(f" Failed to configure audio: {e}")
            # Ensure we close the dialog if stuck
            try:
                self.page.keyboard.press("Escape")
            except:
                pass
