import asyncio
import os
import sys
import time
import requests
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARTIFACT_DIR = r"C:\Users\VEDIKA\.gemini\antigravity\brain\6a47e3fb-6953-4705-8ed7-fb9de099a3ae"
BASE_API = "http://127.0.0.1:8080/api/v1"
FRONTEND_URL = "http://127.0.0.1:5173"

def create_receipt_image(filename="cybersec_receipt.png"):
    img = Image.new("RGB", (1200, 800), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    d.text((80, 80), "GLOBAL CYBER DEFENSE INSTITUTE", fill="black", font=font)
    d.text((80, 160), "Date: 2026-10-23", fill="black", font=font)
    d.text((80, 240), "Invoice #: GCDI-2026-4401", fill="black", font=font)
    d.text((80, 320), "Certification: CISSP Advanced Training & Exam", fill="black", font=font)
    d.text((80, 400), "Taxes (GST 18%): INR 991.52", fill="black", font=font)
    d.text((80, 480), "TOTAL AMOUNT: INR 6,500.00", fill="black", font=font)
    filepath = os.path.abspath(filename)
    img.save(filepath, format="PNG")
    return filepath

def login(email, password="password123"):
    res = requests.post(f"{BASE_API}/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def run_api_workflow_tests():
    print("=" * 70)
    print("1. RUNNING COMPLETE API WORKFLOW VERIFICATION")
    print("=" * 70)

    sub_hdr = login("submitter@example.com")
    rev_hdr = login("reviewer@example.com")
    app_hdr = login("approver@example.com")

    # Step 1: Create draft
    print("\n[Step 1] Submitter creates new claim draft...")
    draft_res = requests.post(f"{BASE_API}/requests", headers=sub_hdr, json={
        "title": "Annual Cybersecurity Certification Reimbursement",
        "description": "Exam and course fee for CISSP certification renewal",
        "request_type": "expense_reimbursement",
        "expense_category": "software",
        "currency": "INR",
        "claimed_amount": 6500.00,
        "expense_date": "2026-10-23",
        "assigned_reviewer_id": 5,
        "assigned_approver_id": 6,
    })
    assert draft_res.status_code == 201, f"Draft creation failed: {draft_res.text}"
    claim = draft_res.json()
    claim_id = claim["id"]
    claim_num = claim["request_number"]
    print(f"  ✓ Created Claim #{claim_num} (ID: {claim_id}) in status '{claim['status']}'")

    # Step 2: Upload receipt document
    print("\n[Step 2] Submitter uploads receipt document...")
    receipt_file = create_receipt_image("test_cert_receipt.png")
    with open(receipt_file, "rb") as f:
        up_res = requests.post(
            f"{BASE_API}/requests/{claim_id}/documents",
            headers=sub_hdr,
            data={"doc_type": "receipt"},
            files={"file": ("cybersec_receipt.png", f, "image/png")}
        )
    assert up_res.status_code == 201, f"Upload failed: {up_res.text}"
    print(f"  ✓ Uploaded document #{up_res.json()['id']} via multipart form-data (HTTP 201)")

    # Wait for document processing
    print("  Waiting for background OCR extraction...")
    for _ in range(12):
        time.sleep(1)
        doc_res = requests.get(f"{BASE_API}/requests/{claim_id}/documents", headers=sub_hdr)
        docs = doc_res.json()
        if docs and docs[0]["processing_status"] in ("ready", "failed"):
            print(f"  ✓ Document OCR completed with status: '{docs[0]['processing_status']}'")
            break

    # Step 3: Submitter submits claim
    print("\n[Step 3] Submitter submits claim for review...")
    sub_res = requests.post(f"{BASE_API}/requests/{claim_id}/submit", headers=sub_hdr)
    assert sub_res.status_code == 200, f"Submit failed: {sub_res.text}"
    submitted_claim = sub_res.json()
    print(f"  ✓ Claim #{claim_num} transitioned to: '{submitted_claim['status']}'")
    assert submitted_claim["status"] == "under_review"

    # Step 4: Verify Queues
    print("\n[Step 4] Checking Role Queues...")
    rev_q = requests.get(f"{BASE_API}/requests/review-queue", headers=rev_hdr).json()
    rev_q_ids = [q["id"] for q in rev_q]
    assert claim_id in rev_q_ids, f"Claim {claim_id} should be in reviewer's queue"
    print(f"  ✓ Claim #{claim_num} is in Reviewer Queue")

    app_q_before = requests.get(f"{BASE_API}/requests/review-queue", headers=app_hdr).json()
    app_q_before_ids = [q["id"] for q in app_q_before]
    assert claim_id not in app_q_before_ids, f"Claim {claim_id} MUST NOT be in approver queue yet"
    print(f"  ✓ Claim #{claim_num} is NOT yet in Approver Queue (correctly awaiting review)")

    # Step 5: Backend Enforcement - Approver cannot approve claim while under_review
    print("\n[Step 5] Backend Permission Enforcement: Approver cannot approve while under_review...")
    premature_app = requests.post(f"{BASE_API}/requests/{claim_id}/approve", headers=app_hdr, json={
        "comment": "Premature approval attempt"
    })
    assert premature_app.status_code == 422, f"Expected 422, got {premature_app.status_code}: {premature_app.text}"
    print(f"  ✓ Premature approval correctly rejected with HTTP 422: {premature_app.json()['detail']}")

    # Step 6: Reviewer checks verification and completes review
    print("\n[Step 6] Reviewer completes verification review...")
    checks_res = requests.get(f"{BASE_API}/requests/{claim_id}/checks", headers=rev_hdr)
    checks = checks_res.json()
    print(f"  Claim has {len(checks)} verification check(s):")
    for c in checks:
        print(f"    - {c['rule_name']}: {c['result']} (severity: {c['severity']}, status: {c['resolution_status']})")
        # If any open flag exists, resolve it with documented rationale
        if c["result"] == "flag" and c["resolution_status"] == "open":
            print(f"    Resolving open flag #{c['id']} with audit reason...")
            res_flag = requests.post(
                f"{BASE_API}/requests/{claim_id}/resolve-check?check_id={c['id']}",
                headers=rev_hdr,
                json={"resolution_status": "resolved", "reason": "Amount verified on official institute invoice"}
            )
            assert res_flag.status_code == 200

    comp_res = requests.post(f"{BASE_API}/requests/{claim_id}/complete-review", headers=rev_hdr, json={
        "comment": "All documents verified against training policy. Invoice amounts match claim."
    })
    assert comp_res.status_code == 200, f"Complete review failed: {comp_res.text}"
    print(f"  ✓ Reviewer successfully completed review and forwarded claim to Approver")

    # Step 7: Check claim status moved to pending_approval
    claim_after_rev = requests.get(f"{BASE_API}/requests/{claim_id}", headers=app_hdr).json()
    assert claim_after_rev["status"] == "pending_approval", f"Expected pending_approval, got {claim_after_rev['status']}"
    print(f"  ✓ Claim #{claim_num} status successfully moved to: 'pending_approval'")

    # Step 8: Verify Approver Queue
    print("\n[Step 8] Verifying Approver Queue...")
    app_q_after = requests.get(f"{BASE_API}/requests/review-queue", headers=app_hdr).json()
    app_q_after_ids = [q["id"] for q in app_q_after]
    assert claim_id in app_q_after_ids, f"Claim {claim_id} must now be in approver queue!"
    print(f"  ✓ Claim #{claim_num} is now active in Approver Decision Queue")

    # Step 9: Submitter cannot self-approve
    print("\n[Step 9] Security Check: Submitter cannot self-approve...")
    self_app = requests.post(f"{BASE_API}/requests/{claim_id}/approve", headers=sub_hdr, json={
        "comment": "Self-approval attempt"
    })
    assert self_app.status_code == 403, f"Expected 403, got {self_app.status_code}"
    print("  ✓ Self-approval correctly blocked with HTTP 403 Forbidden")

    # Step 10: Approver approves claim
    print("\n[Step 10] Approver authorizes and approves claim...")
    decision_reason = "Executive authorization granted under FY26 Professional Development budget."
    approve_res = requests.post(f"{BASE_API}/requests/{claim_id}/approve", headers=app_hdr, json={
        "comment": decision_reason
    })
    assert approve_res.status_code == 200, f"Approval failed: {approve_res.text}"
    final_claim = requests.get(f"{BASE_API}/requests/{claim_id}", headers=app_hdr).json()
    assert final_claim["status"] == "approved"
    print(f"  ✓ Claim #{claim_num} officially transitioned to 'approved'")

    # Step 11: Verify audit trail and review history
    print("\n[Step 11] Verifying Review Actions & Audit Trail...")
    hist_res = requests.get(f"{BASE_API}/requests/{claim_id}/history", headers=app_hdr).json()
    action_types = [h["action_type"] for h in hist_res]
    print(f"  Review Action Sequence: {' -> '.join(action_types)}")
    assert "review_completed" in action_types
    assert "approved" in action_types

    audit_res = requests.get(f"{BASE_API}/audit?request_id={claim_id}", headers=app_hdr).json()
    print(f"  Audit events recorded for claim: {len(audit_res)}")
    assert len(audit_res) > 0

    if os.path.exists(receipt_file):
        os.remove(receipt_file)
    print("\n>>> API WORKFLOW TESTS PASSED 100%! <<<\n")
    return claim_id


async def run_browser_e2e_approval(claim_id: int):
    print("=" * 70)
    print("2. RUNNING BROWSER E2E VERIFICATION (PLAYWRIGHT)")
    print("=" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(viewport={"width": 1440, "height": 950})
        page = await context.new_page()

        # 1. Login as Approver
        print("Logging in as Approver (approver@example.com)...")
        await page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
        await page.fill('input[type="email"]', "approver@example.com")
        await page.fill('input[type="password"]', "password123")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard**", timeout=10000)
        print("  ✓ Logged in as Approver.")

        # 2. Open Claim Detail Page
        print(f"Navigating to Claim #{claim_id}...")
        await page.goto(f"{FRONTEND_URL}/requests/{claim_id}", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # 3. Check for Approver Decision Center UI
        content = await page.content()
        assert "Approver Decision Center" in content, "Approver Decision Center banner missing"
        assert "Claim Officially Approved" in content, "Approval banner missing"
        print("  ✓ Approver Decision Center rendered officially approved state with full certification.")

        # 4. Take Screenshot of Approved State
        screenshot_path = os.path.join(ARTIFACT_DIR, "v8_approver_decision_success.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"  ✓ Saved visual proof screenshot: {screenshot_path}")

        # 5. Also test REQ-2026-0068 in the Approver view to verify no misleading text
        print("\nNavigating to Claim REQ-2026-0068 (Claim 68) to verify under_review state...")
        await page.goto(f"{FRONTEND_URL}/requests/68", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        c68_content = await page.content()
        assert "Under Review" in c68_content or "under review" in c68_content.lower()
        # Verify no fake 'Compliance review completed.' text
        assert "Compliance review completed. Documents verified against company reimbursement policy." not in c68_content
        print("  ✓ Claim REQ-2026-0068 correctly shows Under Review without fake completion text.")

        # 6. Take Screenshot of REQ-2026-0068
        c68_screenshot_path = os.path.join(ARTIFACT_DIR, "v8_claim_68_under_review_approver_view.png")
        await page.screenshot(path=c68_screenshot_path, full_page=True)
        print(f"  ✓ Saved Claim 68 proof screenshot: {c68_screenshot_path}")

        await browser.close()

    print("\n>>> BROWSER E2E VERIFICATIONS PASSED 100%! <<<\n")


if __name__ == "__main__":
    cid = run_api_workflow_tests()
    asyncio.run(run_browser_e2e_approval(cid))
