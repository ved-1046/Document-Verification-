import asyncio
import os
import sys
import requests
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARTIFACT_DIR = r"C:\Users\VEDIKA\.gemini\antigravity\brain\6a47e3fb-6953-4705-8ed7-fb9de099a3ae"
BASE_API = "http://127.0.0.1:8080/api/v1"
FRONTEND_URL = "http://127.0.0.1:5173"

def create_sample_receipt(filename="test_supporting.png"):
    img = Image.new("RGB", (1200, 800), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    d.text((80, 80), "HOTEL TAJ PALACE - SUPPORTING ITEMIZATION", fill="black", font=font)
    d.text((80, 160), "Date: 2026-10-23", fill="black", font=font)
    d.text((80, 240), "Conference Room Rental: INR 4,000.00", fill="black", font=font)
    d.text((80, 320), "Projector & Tech Setup: INR 2,000.00", fill="black", font=font)
    d.text((80, 400), "Tea & Refreshments: INR 2,450.00", fill="black", font=font)
    d.text((80, 480), "TOTAL: INR 8,450.00", fill="black", font=font)
    filepath = os.path.abspath(filename)
    img.save(filepath, format="PNG")
    return filepath

async def test_detail_page_upload():
    print("\n--- 3. Testing Upload directly from Claim Detail View (RequestDetailPage) ---")
    supp_file = create_sample_receipt("claim_detail_upload.png")
    upload_responses = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(viewport={"width": 1440, "height": 950})
        page = await context.new_page()

        def on_response(response):
            if "/documents" in response.url and response.request.method == "POST":
                upload_responses.append({
                    "url": response.url,
                    "status": response.status,
                })
                print(f"  [Network Event] POST {response.url} returned HTTP {response.status}")

        page.on("response", on_response)

        # Login
        await page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
        await page.fill('input[type="email"]', "submitter@example.com")
        await page.fill('input[type="password"]', "password123")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard**", timeout=10000)

        # Open request 67 (created in the previous test)
        await page.goto(f"{FRONTEND_URL}/requests/67", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Click on Step 1 (Upload documents)
        step1_btn = await page.query_selector('button:has-text("Upload documents")')
        if step1_btn:
            print("Clicking 'Upload documents' step button...")
            await step1_btn.click()
            await page.wait_for_timeout(1000)

        # In Step 1, select file for supporting expense form
        form_input = await page.query_selector('#upload-file-form')
        if form_input:
            print("Found #upload-file-form input. Setting file...")
            await form_input.set_input_files(supp_file)
            await page.wait_for_timeout(800)

            # Click 'Start Secure Upload' button
            start_btn = await page.query_selector('button:has-text("Start Secure Upload")')
            assert start_btn is not None, "Could not find 'Start Secure Upload' button"
            print("Clicking 'Start Secure Upload'...")
            await start_btn.click()

            await page.wait_for_timeout(4000)
            print(f"Captured {len(upload_responses)} upload responses from detail page.")
            assert len(upload_responses) >= 1, "No document upload response captured!"
            for r in upload_responses:
                assert r["status"] == 201, f"Expected 201 Created, got {r['status']}"
            print("Claim Detail page upload verification PASSED with HTTP 201!")
            
            # Screenshot of the claim page with both documents
            screenshot_path = os.path.join(ARTIFACT_DIR, "v7_claim_detail_with_uploaded_docs.png")
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"Saved detail proof screenshot to: {screenshot_path}")

        await browser.close()

    if os.path.exists(supp_file):
        os.remove(supp_file)

if __name__ == "__main__":
    asyncio.run(test_detail_page_upload())
