#!/usr/bin/env python3
"""
Quick Deployment Verification for Dashboard Features
Checks: Code presence, function availability, feature implementation
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
CONSOLE_URL = f"{BASE_URL}/console.html"
DASHBOARD_JS_URL = f"{BASE_URL}/frontend/dashboard.js"

def check_server_running():
    """Check if server is running"""
    try:
        response = requests.get(CONSOLE_URL, timeout=5)
        return response.status_code == 200
    except:
        return False

def get_dashboard_js():
    """Get dashboard.js content"""
    try:
        response = requests.get(DASHBOARD_JS_URL, timeout=10)
        return response.text if response.status_code == 200 else None
    except Exception as e:
        print(f"❌ Could not fetch dashboard.js: {e}")
        return None

def verify_deployed_features():
    """Verify all features are deployed"""
    print("\n" + "="*70)
    print("DEPLOYMENT VERIFICATION REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Check 1: Server status
    print("\n1️⃣  SERVER STATUS")
    print("-" * 70)
    if check_server_running():
        print("✅ Server running on http://localhost:8000")
    else:
        print("❌ Server not responding")
        return False
    
    # Check 2: Get dashboard.js
    print("\n2️⃣  FETCHING DASHBOARD.JS")
    print("-" * 70)
    dashboard_js = get_dashboard_js()
    
    if not dashboard_js:
        print("❌ Could not fetch dashboard.js")
        return False
    
    print(f"✅ dashboard.js loaded ({len(dashboard_js)} bytes)")
    
    # Check 3: Feature verification
    print("\n3️⃣  FEATURE VERIFICATION")
    print("-" * 70)
    
    features = {
        "Styled Dialog System": {
            "checks": [
                ("_systemDialogConfig", "Dialog configuration engine"),
                ("styledConfirm", "Promise-based confirm dialog"),
                ("styledAlert", "Promise-based alert dialog"),
            ]
        },
        "Background Carousel": {
            "checks": [
                ("_injectBgCarouselEngine", "Runtime carousel injector"),
                ("_parseBgUrls", "URL list parser"),
                ("_applyBgToEl", "Background element applier"),
                ("toggleBgCarouselOptions", "Carousel UI toggle"),
            ]
        },
        "Animation Effects": {
            "checks": [
                ("_ensureImageAnimationStyles", "Animation keyframe injector"),
                ("_applyImgAnimation", "Per-image animation applier"),
                ("wbImgFloat", "Float animation"),
                ("wbImgZoom", "Zoom animation"),
                ("wbBgDrift", "Background drift effect"),
                ("wbBgZoom", "Background zoom effect"),
                ("wbBgPulse", "Background pulse effect"),
            ]
        },
        "Animation Presets": {
            "checks": [
                ("function applyBgAnimPreset", "Background preset function"),
                ("function applyImgAnimPreset", "Image preset function"),
                ("applyBgAnimPreset('subtle')", "Subtle preset button"),
                ("applyBgAnimPreset('medium')", "Medium preset button"),
                ("applyBgAnimPreset('bold')", "Bold preset button"),
            ]
        },
        "Info Panel Display": {
            "checks": [
                ("📍 Section:", "Section anchor display"),
                ("🖼️ Image:", "Image URL display"),
                ("🔄 Carousel:", "Carousel status display"),
                ("✨ Motion:", "Motion effect display"),
                ("sectionLabel", "Section label parameter"),
            ]
        },
        "Multi-File Upload Fix": {
            "checks": [
                ("bgImageInput_", "Unique upload input IDs"),
                ("secIdx", "Section index parameter"),
                ('accept="image/*" multiple', "Multiple file input"),
            ]
        },
    }
    
    total_checks = 0
    passed_checks = 0
    
    for category, test_group in features.items():
        print(f"\n  {category}")
        for pattern, description in test_group["checks"]:
            total_checks += 1
            if pattern in dashboard_js:
                print(f"    ✅ {description}")
                passed_checks += 1
            else:
                print(f"    ❌ {description}")
    
    # Check 4: Summary
    print("\n4️⃣  SUMMARY")
    print("-" * 70)
    print(f"Features checked: {total_checks}")
    print(f"Features verified: {passed_checks}")
    percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    print(f"Coverage: {percentage:.1f}%")
    
    print("\n" + "="*70)
    if passed_checks == total_checks:
        print("✅ ALL FEATURES DEPLOYED SUCCESSFULLY!")
        print("\n📝 Next Steps:")
        print("   1. Clear browser cache (Ctrl+Shift+Delete)")
        print("   2. Hard refresh (Ctrl+F5)")
        print("   3. Login with sayeesaran")
        print("   4. Follow MANUAL_TEST_GUIDE.md for manual verification")
    else:
        print(f"⚠️  {total_checks - passed_checks} feature(s) not verified")
    
    print("="*70 + "\n")
    
    return passed_checks == total_checks

if __name__ == "__main__":
    import sys
    success = verify_deployed_features()
    sys.exit(0 if success else 1)
