import re

path = 'backend/app/services/document_processing/processor.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''                        if req.claimed_amount is None and "total_amount" in normalized:
                            try:
                                req.claimed_amount = Decimal(normalized["total_amount"])
                            except Exception:
                                pass
                        if req.expense_date is None and "expense_date" in normalized:
                            try:
                                req.expense_date = date.fromisoformat(normalized["expense_date"])
                            except Exception:
                                pass
                        if (not req.currency or req.currency == "INR") and "currency" in normalized:
                            req.currency = normalized["currency"]
                        if "merchant_name" in normalized and normalized["merchant_name"]:'''

new = '''                        if req.claimed_amount is None and normalized.get("total_amount"):
                            try:
                                req.claimed_amount = Decimal(normalized["total_amount"])
                            except Exception:
                                pass
                        if req.expense_date is None and normalized.get("expense_date"):
                            try:
                                req.expense_date = date.fromisoformat(normalized["expense_date"])
                            except Exception:
                                pass
                        if (not req.currency or req.currency == "INR") and normalized.get("currency"):
                            req.currency = normalized["currency"]
                        if normalized.get("merchant_name"):'''

assert old in content, "old not found"
content = content.replace(old, new, 1)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("Patched processor.py successfully")
