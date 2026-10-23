from app.services.document_processing.normalizer import extract_fields


def test_sample_receipt_labels_extract_amount_date_provider_and_reference():
    text = """SAMPLE TRAVEL RECEIPT / INVOICE
DEMO DOCUMENT – NOT A REAL RECEIPT
Sample transport provider
Description
Date
Amount (INR)
Local travel – sample fare
22 Oct 2026
1,700.00
Booking / service fee – sample
22 Oct 2026
300.00
TOTAL (SAMPLE)
2,000.00
Receipt reference: DEMO-TRAVEL-2000
"""
    fields = extract_fields(text)
    assert fields["total_amount"] == "2000.00"
    assert fields["expense_date"] == "2026-10-22"
    assert fields["currency"] == "INR"
    assert fields["merchant_name"] == "Sample Transport Provider"
    assert fields["reference_number"] == "DEMO-TRAVEL-2000"
    assert fields["expense_purpose"] is None


def test_sample_expense_form_extracts_claim_details_without_signature_date():
    text = """SAMPLE – EXPENSE REIMBURSEMENT FORM
Employee / Submitter Details
Field
Sample value
Employee name
Alex Submitter (demo account)
Claim reference
DEMO-TRAVEL-2000
Expense category
Travel
Expense date
22 October 2026
Amount claimed
INR 2,000.00
Business purpose
Local travel for a work-related meeting (sample purpose)
Declaration
Generated solely to test the workflow. This is not an authentic reimbursement form.
Date: 23 October 2026
"""
    fields = extract_fields(text)
    assert fields["employee_name"] == "Alex Submitter (Demo Account)"
    assert fields["reference_number"] == "DEMO-TRAVEL-2000"
    assert fields["expense_date"] == "2026-10-22"
    assert fields["total_amount"] == "2000.00"
    assert fields["expense_purpose"] == "Local travel for a work-related meeting (sample purpose)"


def test_unlabeled_disclaimer_does_not_become_expense_purpose():
    fields = extract_fields("This document was generated for a real reimbursement. Date unknown.")
    assert fields["expense_purpose"] is None


def test_ambiguous_numeric_date_is_not_guessed_but_unambiguous_dates_normalize():
    assert extract_fields("Expense date: 10/11/2026")["expense_date"] is None
    assert extract_fields("Expense date: 22/10/2026")["expense_date"] == "2026-10-22"
    assert extract_fields("Expense date: 10/22/2026")["expense_date"] == "2026-10-22"


def test_receipt_heading_can_be_split_across_ocr_lines():
    fields = extract_fields("ABC\nSTATIONERY\nSYNTHETIC TEST RECEIPT\nDate: 22 October 2026")
    assert fields["merchant_name"] == "ABC Stationery"


def test_unlabeled_body_text_is_not_promoted_to_merchant():
    assert extract_fields("Office supplies\nDate: 22 October 2026")["merchant_name"] is None


def test_total_with_currency_and_thousands_separators_normalizes():
    fields = extract_fields("TOTAL\nINR 1,450.00\nDate: 22 October 2026")
    assert fields["total_amount"] == "1450.00"
    assert fields["currency"] == "INR"


def test_currency_symbols_and_decimal_totals_normalize():
    assert extract_fields("Grand Total: $1,234.50")["total_amount"] == "1234.50"
    assert extract_fields("TOTAL Rs. 450.00")["total_amount"] == "450.00"


def test_missing_or_conflicting_totals_remain_unreadable():
    assert extract_fields("Reference: OCR-TEST-450\nDate: 22 October 2026")["total_amount"] is None
    assert extract_fields("TOTAL INR 450.00\nGRAND TOTAL INR 500.00")["total_amount"] is None


def test_reference_date_and_subtotal_numbers_are_not_selected_as_total():
    text = """Receipt Ref: OCR-TEST-450
Date: 22 October 2026
Subtotal INR 400.00
Tax INR 50.00
"""
    assert extract_fields(text)["total_amount"] is None


def test_title_case_and_alphanumeric_merchant_names():
    # Starbucks Coffee
    text1 = "Starbucks Coffee\nStore #1234\nDate: 22.10.2026\nTotal: $12.50\n"
    fields1 = extract_fields(text1)
    assert fields1["merchant_name"] == "Starbucks Coffee"
    assert fields1["total_amount"] == "12.50"
    assert fields1["currency"] == "USD"
    assert fields1["expense_date"] == "2026-10-22"

    # Uber
    text2 = "Uber\nTrip to Airport\nDate: 2026-10-22\nAmount Paid: INR 850.00\n"
    fields2 = extract_fields(text2)
    assert fields2["merchant_name"] == "Uber"
    assert fields2["total_amount"] == "850.00"

    # Zomato & Blinkit
    text3 = "Zomato\nOrder ID: ZOM-9912\nDate: 22 Oct 2026\nTotal Amount: INR 420.00\n"
    fields3 = extract_fields(text3)
    assert fields3["merchant_name"] == "Zomato"
    assert fields3["reference_number"] == "ZOM-9912"
    assert fields3["total_amount"] == "420.00"

    text4 = "Blinkit\nInstant Grocery\nDate: 22 October 2026\nGrand Total: INR 310.00\n"
    fields4 = extract_fields(text4)
    assert fields4["merchant_name"] == "Blinkit"
    assert fields4["total_amount"] == "310.00"

    # 7-Eleven & 3M
    text5 = "7-Eleven\nStore #402\nDate: 22/10/2026\nTotal: $8.75\n"
    fields5 = extract_fields(text5)
    assert fields5["merchant_name"] == "7-Eleven"
    assert fields5["total_amount"] == "8.75"

    text6 = "3M\nIndustrial Supplies\nDate: 22.10.2026\nTotal Amount Due: $1,500.00\n"
    fields6 = extract_fields(text6)
    assert fields6["merchant_name"] == "3M"
    assert fields6["total_amount"] == "1500.00"


def test_grand_total_alongside_subtotals_taxes_and_tips():
    text = """RECEIPT
Acme Bistro
Subtotal: $45.00
Sales Tax: $3.60
Tip: $5.00
Grand Total: $53.60
Amount Paid: $53.60
Change Due: $6.40
Date: 22 Oct 2026
"""
    fields = extract_fields(text)
    assert fields["total_amount"] == "53.60"
    assert fields["currency"] == "USD"
    assert fields["expense_date"] == "2026-10-22"
    assert fields["merchant_name"] == "Acme Bistro"


def test_tax_total_and_subtotal_do_not_cause_conflict_with_final_total():
    text = """INVOICE
Modern Workspace Solutions
Sub Total: 1000.00
Tax Total: 180.00
Total: INR 1,180.00
Date: 22.10.2026
"""
    fields = extract_fields(text)
    assert fields["total_amount"] == "1180.00"
    assert fields["currency"] == "INR"
    assert fields["merchant_name"] == "Modern Workspace Solutions"


def test_european_currencies_and_number_formats():
    # Euro with symbol and comma decimal separator
    text_eur = "Bistro Paris\nDate: 22.10.2026\nTotal: 45,50 €\n"
    fields_eur = extract_fields(text_eur)
    assert fields_eur["total_amount"] == "45.50"
    assert fields_eur["currency"] == "EUR"
    assert fields_eur["expense_date"] == "2026-10-22"

    # British Pound with symbol
    text_gbp = "London Rail\nDate: 22 Oct 2026\nAmount Paid: £120.00\n"
    fields_gbp = extract_fields(text_gbp)
    assert fields_gbp["total_amount"] == "120.00"
    assert fields_gbp["currency"] == "GBP"

    # CAD
    text_cad = "Toronto Cafe\nDate: 2026-10-22\nTotal: CAD 35.00\n"
    fields_cad = extract_fields(text_cad)
    assert fields_cad["total_amount"] == "35.00"
    assert fields_cad["currency"] == "CAD"


def test_various_date_formats_and_dot_notation():
    assert extract_fields("Date: 22.10.2026")["expense_date"] == "2026-10-22"
    assert extract_fields("Date: 22-Oct-2026")["expense_date"] == "2026-10-22"
    assert extract_fields("Date: October 22, 2026")["expense_date"] == "2026-10-22"
    assert extract_fields("Date: 2026/10/22")["expense_date"] == "2026-10-22"
    assert extract_fields("Date: 22.10.26")["expense_date"] == "2026-10-22"
    # Ambiguous dot format remains None
    assert extract_fields("Date: 05.06.2026")["expense_date"] is None


def test_reference_number_variants():
    assert extract_fields("Bill No: BL-2026-88")["reference_number"] == "BL-2026-88"
    assert extract_fields("Bill #: BL-9921")["reference_number"] == "BL-9921"
    assert extract_fields("Order ID: ORD-55410")["reference_number"] == "ORD-55410"
    assert extract_fields("Txn #: TXN-7712")["reference_number"] == "TXN-7712"
    assert extract_fields("Folio #: FOL-882")["reference_number"] == "FOL-882"
    assert extract_fields("Invoice No: INV-2026-001")["reference_number"] == "INV-2026-001"
    # When missing, reference_number is None without error
    assert extract_fields("Total: $45.00\nDate: 22 Oct 2026")["reference_number"] is None


def test_empty_or_low_quality_text_returns_safe_defaults():
    empty_fields = extract_fields("")
    for name, value in empty_fields.items():
        assert value is None

    garbled = extract_fields("!@#$%^ &*() _+ \n ~`")
    for name, value in garbled.items():
        assert value is None

