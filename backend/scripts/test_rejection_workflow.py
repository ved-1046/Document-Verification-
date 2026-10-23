import os
import time
import requests
from PIL import Image, ImageDraw, ImageFont

BASE_API = 'http://127.0.0.1:8080/api/v1'

def create_receipt_image(filename="rejection_test_receipt.png"):
    img = Image.new("RGB", (1200, 800), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    d.text((80, 80), "LUXURY RESORT & SPA - PRIVATE EVENT", fill="black", font=font)
    d.text((80, 160), "Date: 2026-10-23", fill="black", font=font)
    d.text((80, 240), "Invoice #: LUX-9092", fill="black", font=font)
    d.text((80, 320), "VIP Penthouse Suite & Private Dinner: INR 25,000.00", fill="black", font=font)
    d.text((80, 480), "TOTAL AMOUNT: INR 25,000.00", fill="black", font=font)
    filepath = os.path.abspath(filename)
    img.save(filepath, format="PNG")
    return filepath

def login(email):
    res = requests.post(f'{BASE_API}/auth/login', json={'email': email, 'password': 'password123'})
    token = res.json()["access_token"]
    return {'Authorization': f'Bearer {token}'}

sub_hdr = login('submitter@example.com')
rev_hdr = login('reviewer@example.com')
app_hdr = login('approver@example.com')

# Create claim
r = requests.post(f'{BASE_API}/requests', headers=sub_hdr, json={
    'title': 'VIP Executive Retreat Suite Expense',
    'description': 'Claim to test rejection workflow',
    'request_type': 'expense_reimbursement',
    'expense_category': 'lodging',
    'claimed_amount': 25000.00,
    'expense_date': '2026-10-23',
    'assigned_reviewer_id': 5,
    'assigned_approver_id': 6
}).json()
cid = r['id']
cnum = r['request_number']

# Upload doc
rec_path = create_receipt_image()
with open(rec_path, 'rb') as f:
    up = requests.post(f'{BASE_API}/requests/{cid}/documents', headers=sub_hdr, data={'doc_type': 'receipt'}, files={'file': ('rejection_receipt.png', f, 'image/png')})
assert up.status_code == 201

# Wait for OCR
for _ in range(10):
    time.sleep(1)
    docs = requests.get(f'{BASE_API}/requests/{cid}/documents', headers=sub_hdr).json()
    if docs and docs[0]['processing_status'] in ('ready', 'failed'):
        break

# Submit
sub = requests.post(f'{BASE_API}/requests/{cid}/submit', headers=sub_hdr)
assert sub.status_code == 200

# Reviewer resolves any open flags and completes review with a note
checks = requests.get(f'{BASE_API}/requests/{cid}/checks', headers=rev_hdr).json()
for c in checks:
    if c['result'] == 'flag' and c['resolution_status'] == 'open':
        requests.post(f'{BASE_API}/requests/{cid}/resolve-check?check_id={c["id"]}', headers=rev_hdr, json={'resolution_status': 'resolved', 'reason': 'Flagged luxury spend noted for approver decision.'})

rev = requests.post(f'{BASE_API}/requests/{cid}/complete-review', headers=rev_hdr, json={
    'comment': 'Review complete. Luxury lodging rate exceeds general policy threshold. Forwarding for executive determination.'
})
assert rev.status_code == 200

# Verify in approver queue
q = requests.get(f'{BASE_API}/requests/review-queue', headers=app_hdr).json()
assert cid in [item['id'] for item in q]

# Approver rejects with reason
rej = requests.post(f'{BASE_API}/requests/{cid}/reject', headers=app_hdr, json={
    'comment': 'Reimbursement denied: Amount exceeds non-executive policy limit without prior VP pre-approval.'
})
assert rej.status_code == 200
final_r = requests.get(f'{BASE_API}/requests/{cid}', headers=app_hdr).json()
assert final_r['status'] == 'rejected'

hist = requests.get(f'{BASE_API}/requests/{cid}/history', headers=app_hdr).json()
actions = [h['action_type'] for h in hist]
print(f'Rejection workflow passed for #{cnum}! Actions: {" -> ".join(actions)}')

if os.path.exists(rec_path):
    os.remove(rec_path)
