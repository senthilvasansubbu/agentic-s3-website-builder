#!/usr/bin/env python3
"""
Feature Verification Script
Checks if all changes from April 23, 2026 are present in dashboard.js
"""

import re
import sys

def verify_features():
    """Verify all features are implemented in dashboard.js"""
    
    with open('/workspaces/agentic-s3-website-builder/frontend/dashboard.js', 'r') as f:
        content = f.read()
    
    features = {
        "Styled Dialog System": [
            ("_systemDialogConfig function", "_systemDialogConfig"),
            ("styledConfirm function", "function styledConfirm"),
            ("styledAlert function", "function styledAlert"),
        ],
        "Background Carousel": [
            ("Carousel injection engine", "_injectBgCarouselEngine"),
            ("Parse background URLs", "_parseBgUrls"),
            ("Apply background to element", "_applyBgToEl"),
        ],
        "Animation Effects": [
            ("Image animation styles injector", "_ensureImageAnimationStyles"),
            ("Apply image animation", "_applyImgAnimation"),
            ("Background motion in data attributes", "wbBgMotion"),
        ],
        "Animation Presets": [
            ("Background preset function", "function applyBgAnimPreset"),
            ("Image preset function", "function applyImgAnimPreset"),
            ("Subtle preset button", "applyBgAnimPreset('subtle')"),
            ("Medium preset button", "applyBgAnimPreset('medium')"),
            ("Bold preset button", "applyBgAnimPreset('bold')"),
        ],
        "Info Panel Display": [
            ("Section label parameter", "sectionLabel"),
            ("Background info box", "📍 Section:"),
            ("Image URL display", "🖼️ Image:"),
            ("Carousel status display", "🔄 Carousel:"),
            ("Motion effect display", "✨ Motion:"),
        ],
        "Multi-File Upload Fix": [
            ("Unique upload input ID", "bgImageInput_"),
            ("Section index parameter", "secIdx"),
            ("Multiple file input attribute", 'accept="image/*" multiple'),
        ],
    }
    
    print("=" * 70)
    print("FEATURE VERIFICATION REPORT")
    print("=" * 70)
    
    all_passed = True
    
    for category, checks in features.items():
        print(f"\n📋 {category}")
        print("-" * 70)
        
        for check_name, pattern in checks:
            found = pattern in content
            status = "✅ FOUND" if found else "❌ MISSING"
            print(f"  {status}: {check_name}")
            
            if not found:
                all_passed = False
        
        # Count occurrences
        count = content.count(pattern)
        if count > 1:
            print(f"     (Found {count} occurrences)")
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL FEATURES VERIFIED - Changes are saved correctly!")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME FEATURES MISSING - Please review the code")
        print("=" * 70)
        return 1


def count_lines():
    """Count total lines in dashboard.js"""
    with open('/workspaces/agentic-s3-website-builder/frontend/dashboard.js', 'r') as f:
        lines = f.readlines()
    
    print(f"\n📊 File Statistics:")
    print(f"  Total lines: {len(lines)}")
    print(f"  Last modified: Check git log")
    

if __name__ == "__main__":
    result = verify_features()
    count_lines()
    sys.exit(result)
