import asyncio
import io
import os
import sys
import requests
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\VEDIKA\.gemini\antigravity\brain\6a47e3fb-6953-4705-8ed7-fb9de099a3ae"
BASE_API = "http://127.0.0.1:8080/api/v1"
FRONTEND_URL = "http://127.0.0.1:5173"

def create_sample_receipt(filename="test_receipt.png"):
    img = Image.new("RGB", (1200, 800), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    d.text((80, 80), "HOTEL TAJ PALACE - MUMBAI", fill="black", font=font)
    d.text((80, 160), "Date: 2026-10-23", fill="black", font=font)
    d.text((80, 240), "Invoice #: INV-99081", fill="black", font=font)
    d.text((80, 320), "Dinner & Conference Catering: INR 8,450.00", fill="black", font=font)
    d.text((80, 400), "Taxes (GST 18%): INR 1,521.00", fill="black", font=font)
    d.text((80, 480), "TOTAL AMOUNT: INR 9,971.00", fill="black", font=font)
    filepath = os.path.abspath(filename)
    img.save(filepath, format="PNG")
    return filepath

def test_backend_api_direct():
    print("\n--- 1. Testing Backend Multipart Form API Directly ---")
    login_res = requests.post(f"{BASE_API}/auth/login", json={"email": "submitter@example.com", "password": "password123"})
    assert login_res.status_code == 200, f"Submitter login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create draft
    req_res = requests.post(f"{BASE_API}/requests", json={
        "title": "API Direct Upload Test",
        "description": "Testing multipart doc_type and file parsing",
        "request_type": "expense_reimbursement",
        "currency": "INR",
        "assigned_reviewer_id": 5,
        "assigned_approver_id": 6
    }, headers=headers)
    assert req_res.status_code == 201, f"Create draft failed: {req_res.text}"
    req_id = req_res.json()["id"]
    print(f"Created draft request #{req_id}")

    receipt_file = create_sample_receipt("direct_test_receipt.png")

    with open(receipt_file, "rb") as f:
        files = {"file": ("receipt.png", f, "image/png")}
        data = {"doc_type": "receipt"}
        up_res = requests.post(f"{BASE_API}/requests/{req_id}/documents", headers=headers, data=data, files=files)
        print(f"Upload response status: {up_res.status_code}")
        assert up_res.status_code == 201, f"Expected 201, got {up_res.status_code}: {up_res.text}"
        doc_json = up_res.json()
        print(f"Successfully uploaded doc #{doc_json['id']} ({doc_json['doc_type']}) with status: {doc_json['processing_status']}")
        assert doc_json["doc_type"] == "receipt"

    if os.path.exists(receipt_file):
        os.remove(receipt_file)
    print("Backend API direct upload test PASSED.")


async def test_frontend_browser_e2e():
    print("\n--- 2. Testing End-to-End Upload via Browser (Playwright) ---")
    receipt_file = create_sample_receipt("e2e_browser_receipt.png")
    
    upload_responses = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(viewport={"width": 1440, "height": 950})
        page = await context.new_page()

        # Intercept and log document upload responses
        def on_response(response):
            if "/documents" in response.url and response.request.method == "POST":
                upload_responses.append({
                    "url": response.url,
                    "status": response.status,
                })
                print(f"  [Network Event] POST {response.url} returned HTTP {response.status}")

        page.on("response", on_response)

        # 1. Login
        print("Navigating to login...")
        await page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
        await page.fill('input[type="email"]', "submitter@example.com")
        await page.fill('input[type="password"]', "password123")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard**", timeout=10000)
        print("Logged in successfully as Submitter.")

        # 2. Go to New Request
        print("Navigating to New Request page...")
        await page.goto(f"{FRONTEND_URL}/new-request", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Set receipt file using the explicit id
        print("Setting receipt file on #receipt-input...")
        await page.set_input_files('#receipt-input', receipt_file)
        await page.wait_for_timeout(500)

        # Fill optional purpose if available
        purpose_input = await page.query_selector('input[placeholder*="Client lunch"]')
        if purpose_input:
            await purpose_input.fill("Executive Team Dinner at Gateway Mumbai")

        # Submit the form
        print("Submitting new expense claim form...")
        submit_btn = await page.query_selector('button[type="submit"]')
        assert submit_btn is not None, "Submit button not found"
        await submit_btn.click()

        # Wait for navigation to /requests/{id}
        print("Waiting for navigation to request detail page...")
        await page.wait_for_url(lambda u: "/requests/" in u and u.split("/requests/")[1].isdigit(), timeout=15000)
        current_url = page.url
        print(f"Navigated successfully to: {current_url}")

        # Check upload network responses
        assert len(upload_responses) >= 1, "No /documents network request was made"
        for resp in upload_responses:
            assert resp["status"] == 201, f"Expected 201 Created for document upload, but got {resp['status']}!"
        print(f"All {len(upload_responses)} document upload request(s) returned HTTP 201 Created! (No 422 error!)")

        # Wait for detail page UI to settle
        await page.wait_for_timeout(3000)
        
        # Take screenshot of the newly created claim with uploaded receipt
        screenshot_path = os.path.join(ARTIFACT_DIR, "v7_document_upload_success.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Saved proof screenshot to: {screenshot_path}")

        await browser.close()
        
    if os.path.exists(receipt_file):
        os.remove(receipt_file)
    
    print("\nALL VERIFICATIONS PASSED: Document upload bug is 100% resolved!")

if __name__ == "__main__":
    test_backend_api_direct()
    asyncio.run(test_frontend_browser_e2e())
