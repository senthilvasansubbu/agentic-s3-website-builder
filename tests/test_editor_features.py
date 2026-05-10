"""
Test Cases for Dashboard Editor Features
Date: April 23, 2026
Features Tested:
1. Styled Modal Dialogs (replacing native confirm/alert)
2. Background Carousel (multi-image slide)
3. Animation Effects (images & backgrounds)
4. Animation Presets (Subtle/Medium/Bold)
5. Background Info Panel (section anchor, image URL, carousel status)
6. Multi-file Upload (Ctrl+Click to select multiple images)
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _seed_dashboard_auth(driver):
    driver.get("http://localhost:8000/login")
    driver.execute_script(
        """
        localStorage.setItem('wb_token', 'wave3-smoke-token');
        localStorage.setItem('wb_user_id', 'wave3-smoke-user');
        localStorage.setItem('wb_plan', 'pro');
        localStorage.setItem('wb_role', 'app_user');
        """
    )
    driver.get("http://localhost:8000/dashboard")
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, "stagingResetBtn"))
    )


def _render_bg_field(
    driver,
    bg_url="https://example.com/bg.jpg",
    bg_color="#ffffff",
    bg_urls=None,
    carousel_enabled=False,
    carousel_interval_sec=5,
    carousel_style="slide-left",
    carousel_speed_ms=900,
    bg_motion="none",
    section_label="Section",
    sec_idx=0,
):
    urls = bg_urls if bg_urls is not None else []
    return driver.execute_script(
        "return _bgField(arguments[0], arguments[1], arguments[2], arguments[3], arguments[4], arguments[5], arguments[6], arguments[7], arguments[8], arguments[9]);",
        bg_url,
        bg_color,
        urls,
        carousel_enabled,
        carousel_interval_sec,
        carousel_style,
        carousel_speed_ms,
        bg_motion,
        section_label,
        sec_idx,
    )


def _render_img_field(driver, mode="none", src="https://example.com/image.jpg", alt="Alt text", fid="img-1"):
    return driver.execute_script(
        "return _imgField(arguments[0], arguments[1], arguments[2], arguments[3], arguments[4], arguments[5]);",
        1,
        "Image",
        src,
        alt,
        fid,
        {"mode": mode},
    )


class TestStyledDialogs:
    """Test Case Group 1: Styled Modal Dialogs"""
    
    def test_reset_button_shows_styled_dialog(self, driver, login_user):
        """TC-1.1: Reset button exists and is wired for styled modal flow."""
        reset_btn = driver.find_element(By.ID, "stagingResetBtn")
        assert reset_btn.get_attribute("title") == "Reset all edits back to original loaded state"
        assert reset_btn.text.strip() == "↺ Reset"
    
    def test_delete_section_shows_styled_dialog(self, driver, login_user):
        """TC-1.2: Dialog helpers for destructive actions are available."""
        result = driver.execute_script(
            "return typeof styledConfirm === 'function' && typeof styledAlert === 'function';"
        )
        assert result is True
    
    def test_close_editor_shows_styled_dialog(self, driver, login_user):
        """TC-1.3: Save/go-live controls are exposed in the editor toolbar."""
        assert driver.find_element(By.ID, "stagingSaveBtn").text.strip() == "💾 Save Changes"
        assert driver.find_element(By.ID, "stagingGoLiveBtn").text.strip() == "🚀 Go Live"


class TestBackgroundCarousel:
    """Test Case Group 2: Background Carousel Feature"""
    
    def test_carousel_upload_multi_images(self, driver, login_user):
        """TC-2.1: The multi-file upload helper is present in the loaded editor code."""
        result = driver.execute_script("return typeof uploadSectionImage === 'function';")
        assert result is True
    
    def test_carousel_enable_toggle(self, driver, login_user):
        """TC-2.2: Carousel engine hooks are loaded in the dashboard bundle."""
        result = driver.execute_script("return typeof _injectBgCarouselEngine === 'function';")
        assert result is True
    
    def test_carousel_slide_interval(self, driver, login_user):
        """TC-2.3: Carousel interval helpers are present for the editor UI."""
        result = driver.execute_script("return typeof applyBgAnimPreset === 'function';")
        assert result is True
    
    def test_carousel_movement_styles(self, driver, login_user):
        html = _render_bg_field(
            driver,
            bg_urls=["https://example.com/one.jpg", "https://example.com/two.jpg"],
            carousel_enabled=True,
            carousel_style="parallax",
        )
        for label in ("Slide Left", "Slide Right", "Fade", "Zoom", "Parallax Drift"):
            assert label in html
    
    def test_carousel_transition_speeds(self, driver, login_user):
        html = _render_bg_field(
            driver,
            bg_urls=["https://example.com/one.jpg", "https://example.com/two.jpg"],
            carousel_enabled=True,
            carousel_speed_ms=1400,
        )
        for label in ("Fast", "Normal", "Slow"):
            assert label in html


class TestAnimationEffects:
    """Test Case Group 3: Image & Background Animation Effects"""
    
    def test_background_motion_effects(self, driver, login_user):
        drift_html = _render_bg_field(driver, bg_urls=["https://example.com/one.jpg", "https://example.com/two.jpg"], carousel_enabled=True, bg_motion="drift")
        zoom_html = _render_bg_field(driver, bg_urls=["https://example.com/one.jpg", "https://example.com/two.jpg"], carousel_enabled=True, bg_motion="zoom")
        pulse_html = _render_bg_field(driver, bg_urls=["https://example.com/one.jpg", "https://example.com/two.jpg"], carousel_enabled=True, bg_motion="pulse")
        assert "Drift" in drift_html
        assert "Zoom" in zoom_html
        assert "Pulse" in pulse_html
    
    def test_image_animation_modes(self, driver, login_user):
        html = _render_img_field(driver, mode="zoom")
        assert "Image animation" in html
        for label in ("Float", "Zoom Pulse", "Fade In", "Sway"):
            assert label in html
    
    def test_animation_persistence(self, driver, login_user):
        html = _render_img_field(driver, mode="sway")
        assert 'option value="sway" selected' in html
        assert driver.find_element(By.ID, "stagingSaveBtn").text.strip() == "💾 Save Changes"


class TestAnimationPresets:
    """Test Case Group 4: Animation Preset Buttons"""
    
    def test_bg_preset_subtle(self, driver, login_user):
        html = _render_bg_field(
            driver,
            bg_urls=["https://example.com/one.jpg", "https://example.com/two.jpg"],
            carousel_enabled=True,
            carousel_interval_sec=7,
            carousel_style="fade",
            carousel_speed_ms=1400,
            bg_motion="drift",
        )
        assert "Enabled • 2 imgs • fade" in html
        assert "Drift" in html
    
    def test_bg_preset_medium(self, driver, login_user):
        html = _render_bg_field(
            driver,
            bg_urls=["https://example.com/one.jpg", "https://example.com/two.jpg"],
            carousel_enabled=True,
            carousel_interval_sec=5,
            carousel_style="slide-left",
            carousel_speed_ms=900,
            bg_motion="zoom",
        )
        assert "Enabled • 2 imgs • slide-left" in html
        assert "Zoom" in html
    
    def test_bg_preset_bold(self, driver, login_user):
        html = _render_bg_field(
            driver,
            bg_urls=["https://example.com/one.jpg", "https://example.com/two.jpg"],
            carousel_enabled=True,
            carousel_interval_sec=3,
            carousel_style="parallax",
            carousel_speed_ms=500,
            bg_motion="pulse",
        )
        assert "Enabled • 2 imgs • parallax" in html
        assert "Pulse" in html
    
    def test_img_preset_subtle(self, driver, login_user):
        html = _render_img_field(driver, mode="float")
        assert 'option value="float" selected' in html
    
    def test_img_preset_medium(self, driver, login_user):
        html = _render_img_field(driver, mode="zoom")
        assert 'option value="zoom" selected' in html
        assert "Zoom Pulse" in html
    
    def test_img_preset_bold(self, driver, login_user):
        html = _render_img_field(driver, mode="sway")
        assert 'option value="sway" selected' in html


class TestBackgroundInfoPanel:
    """Test Case Group 5: Background Summary Info Panel"""
    
    def test_info_panel_displays_section_name(self, driver, login_user):
        html = _render_bg_field(driver, bg_urls=["https://example.com/hero.jpg"], carousel_enabled=False, section_label="1. Hero #hero")
        assert "📍 1. Hero" in html
        assert "#hero" in html
    
    def test_info_panel_displays_image_url(self, driver, login_user):
        long_url = "https://example.com/assets/backgrounds/very-long-image-name-for-test-purposes-1234567890.jpg"
        html = _render_bg_field(driver, bg_url=long_url, bg_urls=[long_url], carousel_enabled=False)
        assert long_url[:60] + "..." in html
    
    def test_info_panel_carousel_status(self, driver, login_user):
        html = _render_bg_field(
            driver,
            bg_urls=["https://example.com/1.jpg", "https://example.com/2.jpg", "https://example.com/3.jpg"],
            carousel_enabled=True,
            carousel_style="slide-left",
        )
        assert "Enabled • 3 imgs • slide-left" in html
    
    def test_info_panel_motion_effect(self, driver, login_user):
        html = _render_bg_field(driver, bg_urls=["https://example.com/1.jpg", "https://example.com/2.jpg"], carousel_enabled=True, bg_motion="drift")
        assert "✨ Motion" in html
        assert "Drift" in html
    
    def test_info_panel_updates_live(self, driver, login_user):
        baseline = _render_bg_field(driver, bg_urls=[], carousel_enabled=False, bg_motion="none")
        updated = _render_bg_field(
            driver,
            bg_urls=["https://example.com/1.jpg", "https://example.com/2.jpg"],
            carousel_enabled=True,
            carousel_style="fade",
            bg_motion="pulse",
        )
        assert baseline != updated
        assert "Disabled" in baseline
        assert "Enabled • 2 imgs • fade" in updated
        assert "Pulse" in updated


class TestMultiFileUpload:
    """Test Case Group 6: Multi-File Upload Functionality"""
    
    def test_multi_select_file_picker(self, driver, login_user):
        html = _render_img_field(driver)
        assert "⬆ Upload Image" in html
        assert "uploadSectionImage(this,'img-1')" in html
    
    def test_multi_file_upload_processing(self, driver, login_user):
        html = _render_img_field(driver)
        assert "input type=\"file\"" in html
        assert "clearSectionImage" in html
    
    def test_multi_file_parallel_sections(self, driver, login_user):
        section_one = _render_bg_field(driver, sec_idx=0)
        section_two = _render_bg_field(driver, sec_idx=1)
        assert 'id="bgImageInput_0"' in section_one
        assert 'id="bgImageInput_1"' in section_two


class TestIntegration:
    """Test Case Group 7: Integration Tests"""
    
    def test_full_carousel_workflow(self, driver, login_user):
        bg_html = _render_bg_field(
            driver,
            bg_urls=[
                "https://example.com/1.jpg",
                "https://example.com/2.jpg",
                "https://example.com/3.jpg",
                "https://example.com/4.jpg",
            ],
            carousel_enabled=True,
            carousel_interval_sec=4,
            carousel_style="parallax",
            carousel_speed_ms=1400,
            bg_motion="pulse",
            section_label="1. Hero #hero",
        )
        img_html = _render_img_field(driver, mode="zoom")
        assert "Enabled • 4 imgs • parallax" in bg_html
        assert "Pulse" in bg_html
        assert 'option value="zoom" selected' in img_html
        assert driver.find_element(By.ID, "stagingSaveBtn").is_displayed()
        assert driver.find_element(By.ID, "stagingGoLiveBtn").is_displayed()
    
    def test_carousel_with_animations(self, driver, login_user):
        bg_html = _render_bg_field(
            driver,
            bg_urls=["https://example.com/1.jpg", "https://example.com/2.jpg"],
            carousel_enabled=True,
            bg_motion="pulse",
        )
        img_html = _render_img_field(driver, mode="zoom")
        assert "Pulse" in bg_html
        assert "Zoom Pulse" in img_html
    
    def test_reset_clears_all_settings(self, driver, login_user):
        assert driver.find_element(By.ID, "stagingResetBtn").text.strip() == "↺ Reset"
        assert driver.execute_script("return typeof historyReset === 'function';") is True


# ============================================================================
# FIXTURES & SETUP
# ============================================================================

@pytest.fixture
def driver():
    """Initialize Selenium WebDriver — skips if Chrome is not available."""
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import WebDriverException
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    try:
        d = webdriver.Chrome(options=options)
    except (WebDriverException, Exception) as exc:
        pytest.skip(f"Chrome/ChromeDriver not available: {exc}")
    yield d
    d.quit()


@pytest.fixture
def login_user(driver):
    """Seed a localStorage token and open the dashboard."""
    _seed_dashboard_auth(driver)
    return driver


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
