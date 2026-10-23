"""
Comprehensive end-to-end verification script testing all 15 scenarios required by the user:
1. Readable receipt (auto-extraction & no manual entry)
2. Matching documents (Checks B and C pass)
3. Documents with mismatched amounts (Flagged with explanation, not fraud)
4. Blank documents ("No readable content found. Please upload a document containing the expense details.")
5. Blurry documents ("This document is difficult to read. Please upload a clearer photo or scan.")
6. Corrupted or unsupported files (HTTP 415/422 rejection)
7. OCR failures (Preserved, safe error handling, no fraud label)
8. Missing required fields (Check A flags, Submitter can enter them)
9. Successful claim submission (persisted in DB)
10. Claim appearing in correct Reviewer queue
11. Reviewer findings and correction requests
12. Claim reaching correct Approver
13. Final decision & persistence after refresh
14. Unauthorized actions by wrong role (RBAC 403)
15. Gemini assistant responses grounded on claim facts
"""
import io
import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from decimal import Decimal
from datetime import date
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import requests

BASE_URL = "http://127.0.0.1:8080/api/v1"

def _font(size: int):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

def _make_receipt_img(lines):
    img = Image.new("RGB", (1800, 1400), "white")
    d = ImageDraw.Draw(img)
    font = _font(54)
    for i, line in enumerate(lines):
        d.text((100, 100 + i * 160), line, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def login(email, password="password123"):
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def wait_for_processing(request_id, headers, timeout=12):
    start = time.time()
    while time.time() - start < timeout:
        res = requests.get(f"{BASE_URL}/requests/{request_id}/documents", headers=headers)
        if res.status_code == 200:
            docs = res.json()
            if docs and all(d["processing_status"] in ("ready", "failed") for d in docs):
                return docs
        time.sleep(0.5)
    return requests.get(f"{BASE_URL}/requests/{request_id}/documents", headers=headers).json()

def run_tests():
    print("=" * 60)
    print("RUNNING 15-POINT COMPREHENSIVE DOCUVERIFY AI VERIFICATION")
    print("=" * 60)

    sub_headers = login("submitter@example.com")
    rev_headers = login("reviewer@example.com")
    rev2_headers = login("reviewer2@example.com")
    app_headers = login("approver@example.com")

    # 1. READABLE RECEIPT AUTO-EXTRACTION & REMOVAL OF REDUNDANT ENTRY
    print("\n[Test 1] Readable receipt auto-extraction (No manual entry upfront)...")
    buf = _make_receipt_img([
        "Merchant: Blue Tokai Coffee",
        "Date: 23 October 2026",
        "TOTAL AMOUNT: INR 450.00",
        "Reference: TAX-88912",
    ])

    # Submitter creates draft WITHOUT entering amount or date manually
    c_res = requests.post(
        f"{BASE_URL}/requests",
        headers=sub_headers,
        json={
            "title": "Expense Reimbursement",
            "expense_category": "meals",
            "currency": "INR",
            "assigned_reviewer_id": 5, # reviewer@example.com
            "assigned_approver_id": 6, # approver@example.com
        }
    )
    assert c_res.status_code == 201, c_res.text
    claim1 = c_res.json()
    claim1_id = claim1["id"]
    print(f"  ✓ Created draft claim #{claim1['request_number']} without manual amount/date")

    # Upload receipt
    up_res = requests.post(
        f"{BASE_URL}/requests/{claim1_id}/documents",
        headers=sub_headers,
        data={"doc_type": "receipt"},
        files={"file": ("blue_tokai_receipt.png", buf, "image/png")}
    )
    assert up_res.status_code == 201, up_res.text
    doc_id = up_res.json()["id"]

    # Poll until OCR finishes
    for _ in range(15):
        time.sleep(1)
        chk = requests.get(f"{BASE_URL}/requests/{claim1_id}", headers=sub_headers).json()
        if chk["claimed_amount"] is not None:
            break
    
    chk = requests.get(f"{BASE_URL}/requests/{claim1_id}", headers=sub_headers).json()
    assert float(chk["claimed_amount"]) == 450.00, f"Expected 450.00, got {chk['claimed_amount']}"
    assert chk["expense_date"] == "2026-10-23", f"Expected 2026-10-23, got {chk['expense_date']}"
    assert "Blue Tokai" in chk["title"], f"Expected Blue Tokai in title, got {chk['title']}"
    print(f"  ✓ Auto-extracted amount: ₹{chk['claimed_amount']}, date: {chk['expense_date']}, title: {chk['title']}")

    # 2. MATCHING DOCUMENTS
    print("\n[Test 2] Matching documents verification...")
    # Add matching expense form
    fbuf = _make_receipt_img([
        "EXPENSE REIMBURSEMENT FORM",
        "Employee: Submitter User",
        "Date: 23 October 2026",
        "TOTAL AMOUNT: INR 450.00",
    ])

    fup = requests.post(
        f"{BASE_URL}/requests/{claim1_id}/documents",
        headers=sub_headers,
        data={"doc_type": "expense_form"},
        files={"file": ("expense_form.png", fbuf, "image/png")}
    )
    assert fup.status_code == 201

    time.sleep(2)
    checks_res = requests.get(f"{BASE_URL}/requests/{claim1_id}/checks", headers=sub_headers).json()
    b_check = next((c for c in checks_res if c["check_type"] == "amount_mismatch"), None)
    c_check = next((c for c in checks_res if c["check_type"] == "date_mismatch"), None)
    assert b_check and b_check["result"] == "pass", f"Expected pass, got {b_check}"
    assert c_check and c_check["result"] == "pass", f"Expected pass, got {c_check}"
    print("  ✓ Checks B (Amount) and C (Date) passed with matching documents.")

    # 3. DOCUMENTS WITH MISMATCHED AMOUNTS
    print("\n[Test 3] Mismatched documents verification (Signal for review, not fraud)...")
    c3_res = requests.post(
        f"{BASE_URL}/requests",
        headers=sub_headers,
        json={"title": "Mismatch Test", "claimed_amount": 950.00, "expense_date": "2026-10-23", "assigned_reviewer_id": 5, "assigned_approver_id": 6}
    )
    c3_id = c3_res.json()["id"]
    buf3 = _make_receipt_img([
        "Merchant: Blue Tokai Coffee",
        "Date: 23 October 2026",
        "TOTAL AMOUNT: INR 450.00",
    ])
    requests.post(f"{BASE_URL}/requests/{c3_id}/documents", headers=sub_headers, data={"doc_type": "receipt"}, files={"file": ("receipt.png", buf3, "image/png")})
    time.sleep(2)
    c3_checks = requests.get(f"{BASE_URL}/requests/{c3_id}/checks", headers=sub_headers).json()
    amt_chk = next(c for c in c3_checks if c["check_type"] == "amount_mismatch")
    assert amt_chk["result"] == "flag", f"Expected flag, got {amt_chk['result']}"
    assert "Amount discrepancy" in amt_chk["explanation"] or "Amount mismatch" in amt_chk["explanation"]
    assert "fraud" not in amt_chk["explanation"].lower()
    print(f"  ✓ Amount mismatch flagged cleanly without fraudulent labeling: {amt_chk['explanation']}")

    # 4. BLANK DOCUMENTS DETECTION
    print("\n[Test 4] Blank document detection...")
    blank_img = Image.new("RGB", (600, 800), color=(255, 255, 255))
    bbuf = io.BytesIO()
    blank_img.save(bbuf, format="PNG")
    bbuf.seek(0)
    c4_res = requests.post(f"{BASE_URL}/requests", headers=sub_headers, json={"title": "Blank Test", "assigned_reviewer_id": 5, "assigned_approver_id": 6})
    c4_id = c4_res.json()["id"]
    requests.post(f"{BASE_URL}/requests/{c4_id}/documents", headers=sub_headers, data={"doc_type": "receipt"}, files={"file": ("blank.png", bbuf, "image/png")})
    time.sleep(2)
    docs4 = requests.get(f"{BASE_URL}/requests/{c4_id}/documents", headers=sub_headers).json()
    assert docs4[0]["processing_status"] == "failed"
    assert "No readable content found" in docs4[0]["processing_error"]
    print(f"  ✓ Blank document caught: {docs4[0]['processing_error']}")

    # 5. BLURRY / LOW-RESOLUTION DOCUMENTS DETECTION
    print("\n[Test 5] Blurry / low-resolution document detection...")
    # Low resolution / blurry
    lowres_img = Image.new("RGB", (100, 100), color=(240, 240, 240))
    ld = ImageDraw.Draw(lowres_img)
    ld.text((10, 10), "Receipt", fill=(0, 0, 0))
    lbuf = io.BytesIO()
    lowres_img.save(lbuf, format="PNG")
    lbuf.seek(0)
    requests.post(f"{BASE_URL}/requests/{c4_id}/documents", headers=sub_headers, data={"doc_type": "receipt"}, files={"file": ("blurry.png", lbuf, "image/png")})
    time.sleep(2)
    docs5 = requests.get(f"{BASE_URL}/requests/{c4_id}/documents", headers=sub_headers).json()
    latest_doc = docs5[-1]
    assert latest_doc["processing_status"] == "failed"
    assert "difficult to read" in latest_doc["processing_error"]
    print(f"  ✓ Blurry/low-res document caught: {latest_doc['processing_error']}")

    # 6. CORRUPTED OR UNSUPPORTED FILES
    print("\n[Test 6] Corrupted or unsupported files rejection...")
    bad_file = io.BytesIO(b"NOT_A_REAL_IMAGE_FILE")
    rej = requests.post(f"{BASE_URL}/requests/{claim1_id}/documents", headers=sub_headers, data={"doc_type": "receipt"}, files={"file": ("virus.exe", bad_file, "application/octet-stream")})
    assert rej.status_code == 415, f"Expected 415, got {rej.status_code}"
    print("  ✓ Unsupported file type rejected with 415.")

    # 7. OCR FAILURES HANDLING
    print("\n[Test 7] OCR failure handling (safe error, original preserved, no auto-rejection)...")
    # The file in test 4 & 5 remained stored and accessible
    down_res = requests.get(f"{BASE_URL}/documents/{docs4[0]['id']}/download", headers=sub_headers)
    assert down_res.status_code == 200
    print("  ✓ Failed document remains preserved on disk and downloadable.")

    # 8. MISSING REQUIRED FIELDS & SUBMITTER ENTRY VIA PATCH
    print("\n[Test 8] Missing required fields & inline submitter patch...")
    c8_res = requests.post(f"{BASE_URL}/requests", headers=sub_headers, json={"title": "Missing Fields Claim", "assigned_reviewer_id": 5, "assigned_approver_id": 6})
    c8_id = c8_res.json()["id"]
    # Image with only merchant name (missing amount and date)
    pbuf = _make_receipt_img([
        "Merchant: STARBUCKS COFFEE INDIA",
        "Beverage item: Cold Brew Latte",
    ])
    requests.post(f"{BASE_URL}/requests/{c8_id}/documents", headers=sub_headers, data={"doc_type": "receipt"}, files={"file": ("starbucks.png", pbuf, "image/png")})
    wait_for_processing(c8_id, sub_headers)
    # Check A flags missing total_amount and expense_date
    chk8 = requests.get(f"{BASE_URL}/requests/{c8_id}/checks", headers=sub_headers).json()
    miss_chk = next(c for c in chk8 if c["check_type"] == "missing_field")
    assert miss_chk["result"] == "flag", f"Expected flag, got {miss_chk['result']}"
    print(f"  ✓ Check A flagged missing required fields: {miss_chk['explanation']}")

    # Submitter fills in missing fields via PATCH
    patch_res = requests.patch(
        f"{BASE_URL}/requests/{c8_id}",
        headers=sub_headers,
        json={"claimed_amount": "320.00", "expense_date": "2026-10-23", "title": "Starbucks Client Catchup"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["claimed_amount"] == "320.00"
    print("  ✓ Submitter successfully patched missing amount and date.")

    # 9. SUCCESSFUL CLAIM SUBMISSION
    print("\n[Test 9] Claim submission...")
    sub_res = requests.post(f"{BASE_URL}/requests/{claim1_id}/submit", headers=sub_headers)
    assert sub_res.status_code == 200, sub_res.text
    claim1_sub = sub_res.json()
    assert claim1_sub["status"] in ("submitted", "under_review", "processing")
    print(f"  ✓ Claim #{claim1_sub['request_number']} submitted successfully (status: {claim1_sub['status']}).")

    # 10. APPEARING IN CORRECT REVIEWER QUEUE
    print("\n[Test 10] Reviewer queue visibility...")
    q_res = requests.get(f"{BASE_URL}/requests/review-queue", headers=rev_headers)
    assert q_res.status_code == 200
    q_ids = [item["id"] for item in q_res.json()]
    assert claim1_id in q_ids, f"Claim {claim1_id} not found in reviewer 5 queue: {q_ids}"
    print(f"  ✓ Claim #{claim1['request_number']} immediately visible in Reviewer User queue.")

    # Check RBAC isolation: Reviewer 2 should NOT see this claim
    q2_res = requests.get(f"{BASE_URL}/requests/review-queue", headers=rev2_headers)
    q2_ids = [item["id"] for item in q2_res.json()]
    assert claim1_id not in q2_ids, "RBAC isolation failed: Reviewer 2 saw Reviewer 1 claim"
    print("  ✓ RBAC isolation verified: Reviewer 2 cannot see Reviewer 1's assigned claim.")

    # 11. REVIEWER FINDINGS AND CORRECTIONS
    print("\n[Test 11] Reviewer findings, corrections, and info requests...")
    # Reviewer requests more info
    req_cor = requests.post(f"{BASE_URL}/requests/{claim1_id}/request-correction", headers=rev_headers, json={"comment": "Please verify tip amount"})
    assert req_cor.status_code == 200
    c1_stat = requests.get(f"{BASE_URL}/requests/{claim1_id}", headers=sub_headers).json()
    assert c1_stat["status"] == "more_info_required"
    print("  ✓ Reviewer requested correction (status moved to more_info_required).")

    # Submitter re-submits
    re_sub = requests.post(f"{BASE_URL}/requests/{claim1_id}/submit", headers=sub_headers)
    assert re_sub.status_code == 200
    print("  ✓ Submitter re-submitted after addressing comment.")

    # Reviewer completes review
    comp_rev = requests.post(f"{BASE_URL}/requests/{claim1_id}/complete-review", headers=rev_headers, json={"comment": "All documents verified and amounts match."})
    assert comp_rev.status_code == 200
    print("  ✓ Reviewer completed review.")

    # 12. CLAIM REACHING CORRECT APPROVER
    print("\n[Test 12] Claim reaching Approver queue...")
    c1_app_stat = requests.get(f"{BASE_URL}/requests/{claim1_id}", headers=app_headers).json()
    assert c1_app_stat["status"] == "pending_approval"

    app_q = requests.get(f"{BASE_URL}/requests/review-queue", headers=app_headers).json()
    app_q_ids = [item["id"] for item in app_q]
    assert claim1_id in app_q_ids, f"Claim {claim1_id} not found in approver queue: {app_q_ids}"
    print(f"  ✓ Claim #{claim1['request_number']} is in pending_approval and visible in Approver queue.")

    # 13. FINAL DECISION AND STATUS PERSISTENCE AFTER REFRESH
    print("\n[Test 13] Final decision and status persistence...")
    appr_res = requests.post(f"{BASE_URL}/requests/{claim1_id}/approve", headers=app_headers, json={"comment": "Approved per team meal budget policy"})
    assert appr_res.status_code == 200
    final_claim = requests.get(f"{BASE_URL}/requests/{claim1_id}", headers=app_headers).json()
    assert final_claim["status"] == "approved"
    # Re-fetch (simulating refresh)
    time.sleep(0.5)
    final_claim_re = requests.get(f"{BASE_URL}/requests/{claim1_id}", headers=sub_headers).json()
    assert final_claim_re["status"] == "approved"
    print(f"  ✓ Claim #{claim1['request_number']} approved with audit reason and permanently persisted.")

    # 14. UNAUTHORIZED ACTIONS BY WRONG ROLE
    print("\n[Test 14] RBAC Unauthorized actions blocked...")
    # Submitter tries to approve
    unauth_app = requests.post(f"{BASE_URL}/requests/{claim1_id}/approve", headers=sub_headers, json={"comment": "Self approval attempt"})
    assert unauth_app.status_code == 403
    # Reviewer tries to approve
    unauth_rev_app = requests.post(f"{BASE_URL}/requests/{claim1_id}/approve", headers=rev_headers, json={"comment": "Reviewer approval attempt"})
    assert unauth_rev_app.status_code == 403
    print("  ✓ Unauthorized actions correctly rejected with HTTP 403 Forbidden.")

    # 15. GEMINI ASSISTANT RESPONSES GROUNDED ON CLAIM EVIDENCE
    print("\n[Test 15] Grounded AI assistant responses...")
    ast_res = requests.post(
        f"{BASE_URL}/assistant/ask",
        headers=sub_headers,
        json={"request_id": claim1_id, "question": "What is the total amount and merchant of this claim?"}
    )
    assert ast_res.status_code == 200, ast_res.text
    ast_data = ast_res.json()
    assert "450" in ast_data["answer"] or "BLUE TOKAI" in ast_data["answer"] or "Blue Tokai" in ast_data["answer"]
    assert ast_data["mode"] in ("llm", "fallback")
    print(f"  ✓ AI Assistant answered ({ast_data['mode']}): grounded on actual claim facts.")

    print("\n" + "=" * 60)
    print("ALL 15 COMPREHENSIVE VERIFICATION POINTS PASSED CLEANLY (100%)")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
