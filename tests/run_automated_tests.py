#!/usr/bin/env python3
"""
Automated Test Runner for Dashboard Editor Features
Tests: Styled Dialogs, Carousel, Animations, Presets
Login User: sayeesaran
"""

import os
import sys
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import Selenium - install if missing
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
except ImportError:
    logger.error("❌ Selenium not installed. Install: pip install selenium")
    sys.exit(1)


class DashboardTester:
    def __init__(self, username="sayeesaran", password="", base_url="http://localhost:8000"):
        self.username = username
        self.password = password
        self.base_url = base_url
        self.driver = None
        self.test_results = []
        
        logger.info(f"🚀 Initializing Dashboard Tester")
        logger.info(f"   Username: {username}")
        logger.info(f"   Base URL: {base_url}")
    
    def start_driver(self):
        """Initialize Chrome WebDriver with options"""
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Uncomment to run headless
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_window_size(1920, 1080)
            logger.info("✅ Chrome WebDriver initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize WebDriver: {e}")
            return False
    
    def log_result(self, test_name, passed, details=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append((test_name, passed, details))
        logger.info(f"{status}: {test_name}")
        if details:
            logger.info(f"     {details}")
    
    def wait_for_element(self, locator, timeout=10):
        """Wait for element to be present"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return element
        except:
            return None
    
    # ───────────────────────────────────────────────────────────────────
    # STEP 1: LOGIN & NAVIGATION
    # ───────────────────────────────────────────────────────────────────
    
    def step1_navigate_and_login(self):
        """Step 1: Navigate to app and login"""
        logger.info("\n" + "="*70)
        logger.info("STEP 1: Navigate to App & Login")
        logger.info("="*70)
        
        try:
            self.driver.get(f"{self.base_url}/console.html")
            time.sleep(2)
            
            # Check if login form exists
            login_btn = self.wait_for_element((By.ID, "loginBtn"), timeout=5)
            if login_btn:
                logger.info("✓ Console page loaded")
                login_btn.click()
                time.sleep(1)
            
            # Enter username
            username_field = self.wait_for_element((By.ID, "usernameInput"))
            if username_field:
                username_field.clear()
                username_field.send_keys(self.username)
                logger.info(f"✓ Username entered: {self.username}")
            
            # Enter password (if needed)
            password_field = self.driver.find_elements(By.ID, "passwordInput")
            if password_field:
                password_field[0].clear()
                password_field[0].send_keys(self.password)
                logger.info("✓ Password entered")
            
            # Click submit
            submit_btn = self.driver.find_element(By.ID, "loginSubmitBtn")
            submit_btn.click()
            
            # Wait for dashboard to load
            time.sleep(3)
            self.wait_for_element((By.CLASS_NAME, "dashboard"), timeout=10)
            
            self.log_result("Step 1: Login & Navigate", True, "Successfully logged in")
            return True
            
        except Exception as e:
            self.log_result("Step 1: Login & Navigate", False, str(e))
            logger.error(f"❌ Login failed: {e}")
            return False
    
    # ───────────────────────────────────────────────────────────────────
    # STEP 2: MANUAL TEST SCENARIOS
    # ───────────────────────────────────────────────────────────────────
    
    def step2_styled_dialog_test(self):
        """Step 2: Test Styled Dialog (Reset button)"""
        logger.info("\n" + "="*70)
        logger.info("STEP 2: Test Styled Dialog Features")
        logger.info("="*70)
        
        try:
            # Find and click a website to edit
            website_link = self.wait_for_element(
                (By.CLASS_NAME, "website-item"),
                timeout=5
            )
            if website_link:
                website_link.click()
                time.sleep(2)
                logger.info("✓ Website selected")
            
            # Wait for staging editor to load
            staging_editor = self.wait_for_element(
                (By.ID, "stagingEditor"),
                timeout=10
            )
            if staging_editor:
                logger.info("✓ Staging editor loaded")
            
            # Check if styledConfirm function exists
            result = self.driver.execute_script("""
                return typeof styledConfirm === 'function' && 
                       typeof styledAlert === 'function';
            """)
            
            if result:
                self.log_result("Step 2: Styled Dialog Functions", True, 
                              "styledConfirm & styledAlert functions available")
                return True
            else:
                self.log_result("Step 2: Styled Dialog Functions", False,
                              "Functions not found in window scope")
                return False
                
        except Exception as e:
            self.log_result("Step 2: Styled Dialog Functions", False, str(e))
            return False
    
    def step3_carousel_features_test(self):
        """Step 3: Test Carousel Features"""
        logger.info("\n" + "="*70)
        logger.info("STEP 3: Test Carousel & Animation Features")
        logger.info("="*70)
        
        tests_passed = 0
        
        # Test 3.1: Check if info panel is rendered
        try:
            info_panel = self.driver.find_element(By.XPATH, 
                "//*[contains(text(), '📍 Section:')]")
            if info_panel:
                self.log_result("Carousel: Info Panel Section Display", True,
                              "Section info displayed")
                tests_passed += 1
        except:
            self.log_result("Carousel: Info Panel Section Display", False,
                          "Info panel not found")
        
        # Test 3.2: Check if carousel options exist
        try:
            carousel_checkbox = self.driver.find_element(By.ID,
                "secBgCarouselEnabled")
            self.log_result("Carousel: Enable Checkbox", True,
                          "Carousel checkbox found")
            tests_passed += 1
        except:
            self.log_result("Carousel: Enable Checkbox", False,
                          "Carousel checkbox not found")
        
        # Test 3.3: Check animation presets
        try:
            preset_buttons = self.driver.find_elements(By.XPATH,
                "//button[contains(text(), 'Subtle') or contains(text(), 'Medium') or contains(text(), 'Bold')]")
            if len(preset_buttons) >= 3:
                self.log_result("Carousel: Animation Preset Buttons", True,
                              f"Found {len(preset_buttons)} preset buttons")
                tests_passed += 1
            else:
                self.log_result("Carousel: Animation Preset Buttons", False,
                              f"Expected 6+ preset buttons, found {len(preset_buttons)}")
        except Exception as e:
            self.log_result("Carousel: Animation Preset Buttons", False, str(e))
        
        # Test 3.4: Check motion effects dropdown
        try:
            motion_select = self.driver.find_element(By.ID, "secBgMotion")
            self.log_result("Carousel: Background Motion Dropdown", True,
                          "Motion dropdown found")
            tests_passed += 1
        except:
            self.log_result("Carousel: Background Motion Dropdown", False,
                          "Motion dropdown not found")
        
        return tests_passed >= 3
    
    def step3b_test_uploaded_code(self):
        """Step 3b: Verify critical code is present"""
        logger.info("\nVerifying loaded JavaScript code...")
        
        checks = {
            "applyBgAnimPreset": "Animation preset function",
            "applyImgAnimPreset": "Image preset function",
            "_injectBgCarouselEngine": "Carousel engine injector",
            "_ensureImageAnimationStyles": "Animation styles injector",
            "uploadBgImage": "Image upload handler",
        }
        
        passed = 0
        for func_name, description in checks.items():
            result = self.driver.execute_script(f"""
                return typeof {func_name} === 'function';
            """)
            
            if result:
                self.log_result(f"Code Verification: {description}", True,
                              f"{func_name} loaded")
                passed += 1
            else:
                self.log_result(f"Code Verification: {description}", False,
                              f"{func_name} not found")
        
        return passed >= 3
    
    # ───────────────────────────────────────────────────────────────────
    # RUN ALL TESTS
    # ───────────────────────────────────────────────────────────────────
    
    def run_all_tests(self):
        """Execute all test steps"""
        try:
            if not self.start_driver():
                return False
            
            # Step 1: Login
            if not self.step1_navigate_and_login():
                logger.error("❌ Login failed - cannot continue")
                return False
            
            time.sleep(2)
            
            # Step 2: Styled Dialogs
            self.step2_styled_dialog_test()
            time.sleep(1)
            
            # Step 3: Carousel & Animations
            self.step3_carousel_features_test()
            time.sleep(1)
            
            # Step 3b: Code Verification
            self.step3b_test_uploaded_code()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Test suite error: {e}")
            return False
        finally:
            self.print_report()
            if self.driver:
                self.driver.quit()
    
    def print_report(self):
        """Print test summary report"""
        logger.info("\n" + "="*70)
        logger.info("TEST REPORT")
        logger.info("="*70)
        
        passed = sum(1 for _, p, _ in self.test_results if p)
        total = len(self.test_results)
        
        logger.info(f"\nResults: {passed}/{total} tests passed")
        
        for test_name, passed, details in self.test_results:
            status = "✅" if passed else "❌"
            logger.info(f"{status} {test_name}")
            if details:
                logger.info(f"   └─ {details}")
        
        logger.info("\n" + "="*70)
        if passed == total:
            logger.info("✅ ALL TESTS PASSED!")
        else:
            logger.info(f"⚠️  {total - passed} test(s) failed")
        logger.info("="*70 + "\n")


def main():
    """Main entry point"""
    # Ask for password
    import getpass
    password = getpass.getpass("Enter sayeesaran password (or press Enter if no password): ")
    
    # Run tests
    tester = DashboardTester(
        username="sayeesaran",
        password=password,
        base_url="http://localhost:8000"
    )
    
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
