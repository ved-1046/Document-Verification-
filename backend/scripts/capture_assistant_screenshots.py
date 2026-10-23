import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\VEDIKA\.gemini\antigravity\brain\6a47e3fb-6953-4705-8ed7-fb9de099a3ae"

async def capture_assistant():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(viewport={"width": 1440, "height": 950})
        page = await context.new_page()

        # 1. Submitter views Assistant for Claim 53
        print("Capturing Submitter AI Assistant...")
        await page.goto("http://127.0.0.1:5173/login", wait_until="networkidle")
        await page.fill('input[type="email"]', "submitter@example.com")
        await page.fill('input[type="password"]', "password123")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard**", timeout=10000)

        # Open claim 53 to show the "Ask AI Assistant" button on claim page
        await page.goto("http://127.0.0.1:5173/requests/53", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "v6_claim_with_assistant_button.png"), full_page=False)
        print("  [OK] Captured v6_claim_with_assistant_button.png")

        # Open Assistant page for claim 53
        await page.goto("http://127.0.0.1:5173/assistant?requestId=53", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        # Click the first suggested question
        first_chip = page.locator('button:has-text("What is the current status")').first
        if await first_chip.count() > 0:
            await first_chip.click()
            await page.wait_for_timeout(2500)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "v6_submitter_ai_assistant.png"), full_page=True)
        print("  [OK] Captured v6_submitter_ai_assistant.png")

        # 2. Reviewer views Assistant for Claim 53
        print("Capturing Reviewer AI Assistant...")
        await page.goto("http://127.0.0.1:5173/login", wait_until="networkidle")
        await page.fill('input[type="email"]', "reviewer@example.com")
        await page.fill('input[type="password"]', "password123")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard**", timeout=10000)

        await page.goto("http://127.0.0.1:5173/assistant?requestId=53", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        rev_chip = page.locator('button:has-text("Summarise verification findings")').first
        if await rev_chip.count() > 0:
            await rev_chip.click()
            await page.wait_for_timeout(2500)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "v6_reviewer_ai_assistant.png"), full_page=True)
        print("  [OK] Captured v6_reviewer_ai_assistant.png")

        # 3. Approver views Assistant for Claim 53
        print("Capturing Approver AI Assistant...")
        await page.goto("http://127.0.0.1:5173/login", wait_until="networkidle")
        await page.fill('input[type="email"]', "approver@example.com")
        await page.fill('input[type="password"]', "password123")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard**", timeout=10000)

        await page.goto("http://127.0.0.1:5173/assistant?requestId=53", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        app_chip = page.locator('button:has-text("Summarise this claim")').first
        if await app_chip.count() > 0:
            await app_chip.click()
            await page.wait_for_timeout(2500)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "v6_approver_ai_assistant.png"), full_page=True)
        print("  [OK] Captured v6_approver_ai_assistant.png")

        await browser.close()
        print("All Assistant screenshots captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture_assistant())
