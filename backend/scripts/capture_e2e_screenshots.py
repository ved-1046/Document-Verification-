import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\VEDIKA\.gemini\antigravity\brain\6a47e3fb-6953-4705-8ed7-fb9de099a3ae"

async def capture_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(viewport={"width": 1440, "height": 950})
        page = await context.new_page()

        # 1. Login as Submitter
        print("Logging in as Submitter...")
        await page.goto("http://127.0.0.1:5173/login", wait_until="networkidle")
        await page.fill('input[type="email"]', "submitter@example.com")
        await page.fill('input[type="password"]', "password123")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard**", timeout=10000)

        # 2. Capture New Request (Document-First Interface)
        print("Capturing New Request page...")
        await page.goto("http://127.0.0.1:5173/requests/new", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "v5_doc_first_new_request.png"), full_page=True)
        print("  [OK] Captured v5_doc_first_new_request.png")

        # 3. Open Claim #53 (from our verify script) or latest draft claim
        print("Capturing Submitter Guided 4-Step Claim Workspace...")
        # Get list of requests
        await page.goto("http://127.0.0.1:5173/requests", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        
        # Navigate to claim 53 (approved) or open one
        await page.goto("http://127.0.0.1:5173/requests/53", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "v5_claim_53_detail.png"), full_page=True)
        print("  [OK] Captured v5_claim_53_detail.png")

        # Open claim 52 (which has the Starbucks partial receipt and inline patch)
        await page.goto("http://127.0.0.1:5173/requests/52", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "v5_submitter_claim_detail_steps.png"), full_page=True)
        print("  [OK] Captured v5_submitter_claim_detail_steps.png")

        # 4. Reviewer View
        print("Switching to Reviewer...")
        await page.goto("http://127.0.0.1:5173/login", wait_until="networkidle")
        await page.fill('input[type="email"]', "reviewer@example.com")
        await page.fill('input[type="password"]', "password123")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard**", timeout=10000)

        # Review queue
        await page.goto("http://127.0.0.1:5173/review-queue", wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "v5_reviewer_queue.png"), full_page=True)
        print("  [OK] Captured v5_reviewer_queue.png")

        # Reviewer workbench
        # Look for any 'Review Evidence' link
        review_link = page.locator('a:has-text("Review Evidence")').first
        if await review_link.count() > 0:
            await review_link.click()
            await page.wait_for_timeout(2000)
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, "v5_reviewer_workbench.png"), full_page=True)
            print("  [OK] Captured v5_reviewer_workbench.png")

        await browser.close()
        print("All screenshots captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture_all())
