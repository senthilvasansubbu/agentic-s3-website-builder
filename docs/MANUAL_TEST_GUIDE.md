# Manual Testing Guide - April 23 Updates
## Dashboard Editor: Carousel, Animations & Dialogs

**Test User:** `sayeesaran`  
**Date:** April 23, 2026  
**Environment:** Local staging editor

---

## PREREQUISITE: Ensure You Have Fresh Code

Before testing, **MUST DO:**

```bash
# 1. Clear browser cache completely
- Press Ctrl+Shift+Delete (Windows) or Cmd+Shift+Delete (Mac)
- Select "All time"
- Check: Cookies, Cache, Cached images and files
- Click "Clear data"

# 2. Hard refresh the page
- Press Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)
- Wait 3 seconds for page to fully load

# 3. Open DevTools and disable cache
- Press F12
- Click Settings (⚙️) in DevTools
- Check "Disable cache (while DevTools open)"
```

---

## TEST SUITE 1: Styled Dialogs ✅

### Test 1.1: Reset Button Dialog
**Steps:**
1. Login as `sayeesaran`
2. Go to any website's staging editor
3. Click **"↺ Reset"** button (top right)
4. **Verify:** A styled modal dialog appears (NOT a browser alert)
5. Click **"Cancel"** → Dialog closes
6. Click **"↺ Reset"** again, click **"Reset"** → Confirmation occurs

**Expected:** Beautiful custom styled dialog instead of browser confirm()

---

## TEST SUITE 2: Background Carousel 🎠

### Test 2.1: Upload Multiple Images (CRITICAL)
**Steps:**
1. Edit a section in staging editor
2. Scroll to **"🎨 Section Background"**
3. Click **"⬆ Upload BG Image(s)"** button
4. In file picker:
   - Select first image
   - **Hold Ctrl** and click 2 more images (or Shift+click for range)
   - Click "Open"
5. **Verify:** Multiple images upload
6. **Check:** Info panel shows all 3 images in textarea

**Expected:** 3 images in "Background Image URLs" textarea

---

### Test 2.2: Enable Carousel
**Steps:**
1. Have 2+ background images uploaded
2. Look for checkbox: **"Enable carousel slide for background images"**
3. Check ✓ the checkbox
4. **Verify:** These options appear:
   - "Slide every [_] seconds"
   - "Movement style" dropdown
   - "Transition speed" dropdown
5. Click **"Apply to Preview"**
6. **Verify:** Images slide in preview

**Expected:** Carousel transitions visible in staging preview

---

### Test 2.3: Configure Carousel Settings
**Steps:**
1. Set "Slide every" to **5** seconds
2. Set "Movement style" to **"Slide Left"**
3. Set "Transition speed" to **"Normal"**
4. Click **"Apply to Preview"**
5. **Watch preview** for 15 seconds

**Expected:** Each image slides left every 5 seconds smoothly

---

### Test 2.4: Test All Movement Styles
Repeat for each style:

| Style | What to expect |
|-------|-----------------|
| Slide Left | Image slides from right to left |
| Slide Right | Image slides from left to right |
| Fade | Image fades out, next fades in |
| Zoom | Image zooms in, next zooms in |
| Parallax Drift | Image drifts with parallax effect |

---

## TEST SUITE 3: Background Motion Effects 🌊

### Test 3.1: Apply Background Motion
**Steps:**
1. Have carousel enabled with images
2. Find **"Background motion"** dropdown
3. Select each option and click **"Apply to Preview":**
   - None (no animation)
   - Drift (subtle movement)
   - Slow Zoom (zooming in slowly)
   - Breathing Pulse (pulsing effect)

**Expected:** Background animates during carousel transitions

---

## TEST SUITE 4: Animation Presets ⚡

### Test 4.1: Subtle Preset
**Steps:**
1. Enable carousel (2+ images)
2. Click **"Subtle"** button (under Background motion)
3. **Verify dropdowns update:** Expected values:
   - Background motion: Drift
   - Movement style: Fade
   - Transition speed: Slow
   - Slide interval: 7 seconds
4. Click **"Apply to Preview"**

**Expected:** Smooth, slow carousel with fade transitions

---

### Test 4.2: Medium Preset
**Steps:**
1. Click **"Medium"** button
2. **Verify:** Expected values:
   - Background motion: Slow Zoom
   - Movement style: Slide Left
   - Transition speed: Normal
   - Slide interval: 5 seconds

**Expected:** Balanced carousel with moderate animations

---

### Test 4.3: Bold Preset
**Steps:**
1. Click **"Bold"** button
2. **Verify:** Expected values:
   - Background motion: Breathing Pulse
   - Movement style: Parallax Drift
   - Transition speed: Fast
   - Slide interval: 3 seconds

**Expected:** Fast, energetic carousel with pulse effect

---

## TEST SUITE 5: Info Panel Display 📊

### Test 5.1: Info Panel Visibility
**Steps:**
1. Select any section to edit
2. Scroll to Background section
3. **Look for info box** with:
   - 📍 Section: [name and anchor]
   - 🖼️ Image: [URL preview]
   - 🔄 Carousel: [status]
   - ✨ Motion: [effect name]

**Expected:** Visual summary of all background settings

---

### Test 5.2: Info Panel Updates
**Steps:**
1. Change a carousel setting (e.g., interval from 5 to 8)
2. **Watch info panel** update in real-time
3. Change motion effect
4. **Verify:** Panel updates immediately

**Expected:** Live updates as you change settings

---

## TEST SUITE 6: Image Animations 🖼️

### Test 6.1: Apply Image Animation
**Steps:**
1. Select a section with an image
2. Find **"Image animation"** dropdown for that image
3. Try each option:
   - None
   - Float (levitates)
   - Zoom Pulse (pulses zoom)
   - Fade In
   - Sway (side-to-side)
4. Click **"Apply to Preview"**

**Expected:** Image animates with selected effect

---

### Test 6.2: Image Animation Presets
**Steps:**
1. Find image section
2. Click **"Subtle"** (below Image animation) → Should be "Float"
3. Click **"Medium"** (same button) → Should be "Zoom Pulse"
4. Click **"Bold"** (same button) → Should be "Sway"

**Expected:** Quick animation switching with preset buttons

---

## TEST SUITE 7: Persistence Test 💾

### Test 7.1: Save & Reload
**Steps:**
1. Configure carousel with:
   - 3 images
   - Slide Left style
   - 5 second interval
   - Drift motion
2. Click **"💾 Save Changes"**
3. Refresh page (Ctrl+R)
4. Re-open the same section

**Expected:** All carousel/animation settings still there ✅

---

## TEST SUITE 8: Integration Tests 🔗

### Test 8.1: Carousel + Image Animation Together
**Steps:**
1. Create carousel (3+ images)
2. Add image to same section
3. Apply "Zoom Pulse" animation to image
4. Set background motion to "Breathing Pulse"
5. Click "Apply to Preview"
6. **Watch for 15 seconds**

**Expected:** Carousel rotates while image pulses (2 animations running)

---

## TROUBLESHOOTING

### Issue: Changes not showing
**Solution:**
```bash
# Force complete refresh
1. Close all tabs with the site
2. Clear cache (Ctrl+Shift+Delete)
3. Reopen site in new tab
4. Hard refresh (Ctrl+F5)
5. Login again as sayeesaran
```

### Issue: File upload doesn't accept multiple files
**Solution:**
```bash
# Ensure you're using the correct method:
- Click "⬆ Upload BG Image(s)"
- In file picker: Hold Ctrl + Click (or Cmd on Mac)
- Select 2-3 images
- Click "Open"
```

### Issue: Dialog not showing (still sees browser confirm)
**Solution:**
```bash
# Verify code is loaded:
1. Open DevTools (F12)
2. Search: Ctrl+F in Sources
3. Search for: "styledConfirm"
4. If not found, code didn't load - clear cache again
```

---

## SIGN-OFF

**Print this checklist and verify:**

- [ ] Styled dialogs appear (not browser alerts)
- [ ] Multi-image upload works with Ctrl+Click
- [ ] Carousel enables and displays options
- [ ] All 5 movement styles transition smoothly
- [ ] All 4 motion effects animate background
- [ ] Preset buttons update dropdowns
- [ ] Info panel shows section/image/carousel status
- [ ] Image animations work (Float, Zoom, Fade, Sway)
- [ ] Image preset buttons work
- [ ] Settings persist after save/refresh

**If all checked:** ✅ **All features working correctly!**

---

## EMERGENCY RESET

If something is broken, run:

```bash
cd /workspaces/agentic-s3-website-builder

# View changes made
git diff frontend/dashboard.js | head -100

# If you need to revert
git checkout frontend/dashboard.js
```

