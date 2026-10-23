import sys
from pathlib import Path

path = Path("frontend/src/pages/RequestDetailPage.tsx")
content = path.read_text(encoding="utf-8")

# 1. Update step completion definitions
old_defs = """    // Step completion conditions (Strictly verified)
    const isStep1Complete = Boolean(
        request.claimed_amount != null &&
        Number(request.claimed_amount) > 0 &&
        request.expense_date &&
        request.assigned_reviewer_id &&
        request.assigned_approver_id
    );
    const hasReadyDoc = Boolean(
        (latestExpenseForm && latestExpenseForm.processing_status === 'ready') ||
        (latestReceipt && latestReceipt.processing_status === 'ready')
    );
    const hasPendingDoc = documents.some((doc) => doc.processing_status === 'processing' || doc.processing_status === 'pending');
    const hasFailedDoc = documents.some((doc) => doc.processing_status === 'failed');

    const isStep2Complete = hasReadyDoc && !hasPendingDoc && !hasFailedDoc;
    const isStep3Complete = Boolean(
        isStep2Complete &&
        (receiptAmountEff.value || formAmountEff.value || request.claimed_amount)
    );
    const isStep4Complete = request.status !== 'draft';

    // Reason why submission is currently disabled
    let submissionBlockReason: string | null = null;
    if (!request.claimed_amount) {
        submissionBlockReason = 'Please enter the expense amount.';
    } else if (!request.expense_date) {
        submissionBlockReason = 'Please enter the expense date.';
    } else if (!latestReceipt && !latestExpenseForm) {
        submissionBlockReason = 'Please upload at least one document (receipt or expense form).';
    } else if (hasPendingDoc) {
        submissionBlockReason = 'Your document is still being processed. Please wait before submitting.';
    } else if (hasFailedDoc) {
        submissionBlockReason = "We couldn't process this document. Please try a clearer copy.";
    } else if (!request.assigned_reviewer_id || !request.assigned_approver_id) {
        submissionBlockReason = 'Please select an active reviewer and approver.';
    }"""

new_defs = """    // Modern 4-step workflow completion conditions
    const hasReadyDoc = Boolean(
        (latestExpenseForm && latestExpenseForm.processing_status === 'ready') ||
        (latestReceipt && latestReceipt.processing_status === 'ready')
    );
    const hasPendingDoc = documents.some((doc) => doc.processing_status === 'processing' || doc.processing_status === 'pending');
    const hasFailedDoc = documents.some((doc) => doc.processing_status === 'failed');

    // Step 1: Upload Documents (complete when at least 1 document uploaded and ready)
    const isStep1Complete = hasReadyDoc && !hasPendingDoc && !hasFailedDoc;

    // Step 2: Extracted Details & Missing Fields (complete when amount and date are confirmed)
    const isStep2Complete = Boolean(
        isStep1Complete &&
        request.claimed_amount != null &&
        Number(request.claimed_amount) > 0 &&
        request.expense_date &&
        request.assigned_reviewer_id &&
        request.assigned_approver_id
    );

    // Step 3: Verification Checks (complete when checks have been run)
    const isStep3Complete = Boolean(isStep2Complete && checks.length > 0);

    // Step 4: Submitted (complete when status is no longer draft)
    const isStep4Complete = request.status !== 'draft';

    // Reason why submission is currently disabled
    let submissionBlockReason: string | null = null;
    if (!latestReceipt && !latestExpenseForm) {
        submissionBlockReason = 'Please upload a receipt or expense document in Step 1.';
    } else if (hasPendingDoc) {
        submissionBlockReason = 'Your document is still being processed. Please wait for OCR extraction to complete.';
    } else if (hasFailedDoc) {
        submissionBlockReason = latestReceipt?.processing_error || "Document processing failed. Please upload a clearer copy in Step 1.";
    } else if (!request.claimed_amount) {
        submissionBlockReason = 'Please confirm or enter the claimed amount in Step 2.';
    } else if (!request.expense_date) {
        submissionBlockReason = 'Please confirm or select the expense date in Step 2.';
    } else if (!request.assigned_reviewer_id || !request.assigned_approver_id) {
        submissionBlockReason = 'Please select an active reviewer and approver in Step 2.';
    }"""

if old_defs in content:
    content = content.replace(old_defs, new_defs)
    print("Replaced step definitions")
else:
    print("Could not match old_defs")

# 2. Replace the guided submission wizard UI
start_marker = ") : isDraftMode ? ("
end_marker = "                    {/* Expandable Technical Audit Drawer */}"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    print(f"Found draft mode wizard block: {start_idx} to {end_idx}")
    new_wizard = """) : isDraftMode ? (
                <div className="space-y-6">
                    {/* 4-Step Progress Indicator */}
                    <div className="card p-5">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-surface-border pb-3">
                            <div>
                                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700">
                                    Guided Claim Workflow
                                </span>
                                <h2 className="text-base font-bold text-main">
                                    Step {wizardStep} of 4: {
                                        wizardStep === 1 ? 'Upload documents' :
                                        wizardStep === 2 ? 'Review extracted details' :
                                        wizardStep === 3 ? 'Document verification' :
                                        'Review and submit'
                                    }
                                </h2>
                            </div>
                            <p className="text-xs font-semibold text-muted">
                                Draft claim saved · You control when to submit
                            </p>
                        </div>

                        {/* Interactive Step Buttons */}
                        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                            {[
                                { num: 1, label: 'Upload documents', complete: isStep1Complete },
                                { num: 2, label: 'Extracted details', complete: isStep2Complete },
                                { num: 3, label: 'Verification', complete: isStep3Complete },
                                { num: 4, label: 'Submit', complete: isStep4Complete },
                            ].map(({ num, label, complete }) => {
                                const current = wizardStep === num;
                                return (
                                    <button
                                        key={num}
                                        type="button"
                                        onClick={() => setWizardStep(num)}
                                        className={`flex items-center gap-3 rounded-xl border p-3 text-left transition ${
                                            current
                                                ? 'border-indigo-600 bg-indigo-50/70 text-indigo-950 ring-2 ring-indigo-100 shadow-xs'
                                                : complete
                                                ? 'border-teal-200 bg-teal-50/40 text-teal-950 hover:bg-teal-50/70'
                                                : 'border-surface-border bg-white text-muted hover:bg-slate-50'
                                        }`}
                                    >
                                        <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                                            complete
                                                ? 'bg-teal-600 text-white'
                                                : current
                                                ? 'bg-indigo-700 text-white shadow-xs'
                                                : 'bg-slate-200 text-slate-600'
                                        }`}>
                                            {complete ? '✓' : num}
                                        </span>
                                        <div className="min-w-0 flex-1">
                                            <p className={`truncate text-xs font-bold ${current ? 'text-indigo-950' : complete ? 'text-teal-900' : 'text-main'}`}>
                                                {label}
                                            </p>
                                            <p className="text-[10px] text-muted">
                                                {complete ? 'Completed' : current ? 'In progress' : 'Upcoming'}
                                            </p>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* STEP 1: Upload documents */}
                    {wizardStep === 1 && (
                        <section className="card p-6 space-y-5">
                            <div className="border-b border-surface-border pb-3">
                                <h3 className="text-base font-bold text-main">Step 1 — Upload documents</h3>
                                <p className="mt-1 text-xs text-muted">
                                    Upload your receipt or invoice. DocuVerify AI automatically extracts merchant, date, amount, and currency.
                                </p>
                            </div>

                            {/* Notice distinguishing uploading from submitting */}
                            <div className="rounded-xl border border-indigo-200/70 bg-indigo-50/50 p-4 text-xs leading-relaxed text-indigo-950 font-medium">
                                <strong>How it works:</strong> Uploading runs automated OCR extraction. In Step 2, you will review the extracted details and fill any missing information before submitting.
                            </div>

                            {/* Document Cards explaining state & action */}
                            <div className="grid gap-4 md:grid-cols-2">
                                {/* 1. Receipt / Invoice (Primary) */}
                                {(() => {
                                    const latest = latestReceipt;
                                    const cleanFields = latest ? (extractions[latest.id] ?? []).filter((f) => f.field_name !== '_raw_page_text') : [];
                                    const isFailed = latest?.processing_status === 'failed';
                                    const isProcessing = latest?.processing_status === 'processing' || latest?.processing_status === 'pending';
                                    const isReady = latest?.processing_status === 'ready';

                                    return (
                                        <div className="rounded-xl border border-surface-border bg-slate-50/60 p-4 space-y-3">
                                            <div className="flex items-start justify-between gap-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-indigo-700 shadow-xs ring-1 ring-slate-200">
                                                        <Receipt className="h-4 w-4" />
                                                    </span>
                                                    <div>
                                                        <h4 className="text-xs font-bold text-main">Receipt or Invoice <span className="text-red-600">*</span></h4>
                                                        <p className="text-[10px] text-muted">Proof showing merchant, date & total amount</p>
                                                    </div>
                                                </div>
                                                {latest ? (
                                                    <span className={`badge ${isReady ? 'bg-teal-50 text-teal-700 ring-teal-200' : isFailed ? 'bg-red-50 text-red-700 ring-red-200' : 'bg-amber-50 text-amber-800 ring-amber-200'}`}>
                                                        <span className="h-1.5 w-1.5 rounded-full bg-current" />
                                                        {latest.processing_status}
                                                    </span>
                                                ) : (
                                                    <span className="rounded-full bg-white px-2 py-0.5 text-[9px] font-bold text-muted ring-1 ring-surface-border">
                                                        Required
                                                    </span>
                                                )}
                                            </div>

                                            {/* Error Message banner if failed (Blank, Blurry, Unreadable) */}
                                            {isFailed && (
                                                <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-900 space-y-1.5">
                                                    <p className="font-bold flex items-center gap-1.5 text-red-800">
                                                        <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
                                                        Document could not be extracted
                                                    </p>
                                                    <p className="text-[11px] leading-relaxed text-red-700 font-medium">
                                                        {latest.processing_error || "This document could not be read. Please upload a clearer copy or scan."}
                                                    </p>
                                                </div>
                                            )}

                                            {/* Details & States */}
                                            <div className="rounded-xl bg-white p-3 text-[11px] space-y-1.5 border border-surface-border shadow-xs">
                                                <div className="flex justify-between">
                                                    <span className="text-muted">Filename:</span>
                                                    <span className="font-semibold text-main truncate max-w-[170px]">{latest?.original_filename ?? 'None uploaded'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-muted">Upload status:</span>
                                                    <span className="font-semibold text-main">{latest ? `Uploaded (v${latest.version_number})` : 'Not uploaded'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-muted">Extraction status:</span>
                                                    <span className="font-semibold text-main">
                                                        {isReady
                                                            ? `Extracted (${cleanFields.length} fields)`
                                                            : isProcessing
                                                            ? 'Reading document text…'
                                                            : isFailed
                                                            ? 'Extraction failed'
                                                            : 'Waiting for upload'}
                                                    </span>
                                                </div>
                                            </div>

                                            {/* Action buttons */}
                                            <div className="flex flex-col gap-2 pt-1">
                                                {isFailed && (
                                                    <button
                                                        type="button"
                                                        className="btn-secondary text-[11px] py-1.5 px-3 w-full flex items-center justify-center gap-1.5"
                                                        onClick={() => retryDocument(latest.id)}
                                                    >
                                                        <RotateCw className="h-3 w-3" /> Retry extraction
                                                    </button>
                                                )}

                                                <input
                                                    id="upload-file-receipt"
                                                    type="file"
                                                    className="sr-only"
                                                    accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                                                    onChange={(e) => {
                                                        setUploadType('receipt');
                                                        setUploadFile(e.target.files?.[0] ?? null);
                                                    }}
                                                />
                                                <button
                                                    type="button"
                                                    className="btn-secondary w-full text-xs py-2 flex items-center justify-center gap-1.5"
                                                    onClick={() => document.getElementById('upload-file-receipt')?.click()}
                                                >
                                                    <Upload className="h-3.5 w-3.5" />
                                                    {isFailed ? 'Upload clearer photo / scan' : latest ? 'Upload replacement receipt' : 'Choose receipt file'}
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })()}

                                {/* 2. Expense Form / Supporting Document (Optional) */}
                                {(() => {
                                    const latest = latestExpenseForm;
                                    const cleanFields = latest ? (extractions[latest.id] ?? []).filter((f) => f.field_name !== '_raw_page_text') : [];
                                    const isFailed = latest?.processing_status === 'failed';
                                    const isProcessing = latest?.processing_status === 'processing' || latest?.processing_status === 'pending';
                                    const isReady = latest?.processing_status === 'ready';

                                    return (
                                        <div className="rounded-xl border border-surface-border bg-slate-50/60 p-4 space-y-3">
                                            <div className="flex items-start justify-between gap-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white text-indigo-700 shadow-xs ring-1 ring-slate-200">
                                                        <FileCheck2 className="h-4 w-4" />
                                                    </span>
                                                    <div>
                                                        <h4 className="text-xs font-bold text-main">Expense Form (Optional)</h4>
                                                        <p className="text-[10px] text-muted">Completed reimbursement form if applicable</p>
                                                    </div>
                                                </div>
                                                {latest ? (
                                                    <span className={`badge ${isReady ? 'bg-teal-50 text-teal-700 ring-teal-200' : isFailed ? 'bg-red-50 text-red-700 ring-red-200' : 'bg-amber-50 text-amber-800 ring-amber-200'}`}>
                                                        <span className="h-1.5 w-1.5 rounded-full bg-current" />
                                                        {latest.processing_status}
                                                    </span>
                                                ) : (
                                                    <span className="rounded-full bg-white px-2 py-0.5 text-[9px] font-bold text-slate-500 ring-1 ring-surface-border">
                                                        Optional
                                                    </span>
                                                )}
                                            </div>

                                            {isFailed && (
                                                <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-900 space-y-1.5">
                                                    <p className="font-bold flex items-center gap-1.5 text-red-800">
                                                        <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
                                                        Document could not be extracted
                                                    </p>
                                                    <p className="text-[11px] leading-relaxed text-red-700 font-medium">
                                                        {latest.processing_error || "Could not extract this document. Upload a clearer scan or PDF."}
                                                    </p>
                                                </div>
                                            )}

                                            <div className="rounded-xl bg-white p-3 text-[11px] space-y-1.5 border border-surface-border shadow-xs">
                                                <div className="flex justify-between">
                                                    <span className="text-muted">Filename:</span>
                                                    <span className="font-semibold text-main truncate max-w-[170px]">{latest?.original_filename ?? 'None uploaded'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-muted">Upload status:</span>
                                                    <span className="font-semibold text-main">{latest ? `Uploaded (v${latest.version_number})` : 'Not uploaded'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-muted">Extraction status:</span>
                                                    <span className="font-semibold text-main">
                                                        {isReady
                                                            ? `Extracted (${cleanFields.length} fields)`
                                                            : isProcessing
                                                            ? 'Reading document text…'
                                                            : isFailed
                                                            ? 'Extraction failed'
                                                            : 'Not attached'}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="flex flex-col gap-2 pt-1">
                                                {isFailed && (
                                                    <button
                                                        type="button"
                                                        className="btn-secondary text-[11px] py-1.5 px-3 w-full flex items-center justify-center gap-1.5"
                                                        onClick={() => retryDocument(latest.id)}
                                                    >
                                                        <RotateCw className="h-3 w-3" /> Retry extraction
                                                    </button>
                                                )}

                                                <input
                                                    id="upload-file-form"
                                                    type="file"
                                                    className="sr-only"
                                                    accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                                                    onChange={(e) => {
                                                        setUploadType('expense_form');
                                                        setUploadFile(e.target.files?.[0] ?? null);
                                                    }}
                                                />
                                                <button
                                                    type="button"
                                                    className="btn-secondary w-full text-xs py-2 flex items-center justify-center gap-1.5"
                                                    onClick={() => document.getElementById('upload-file-form')?.click()}
                                                >
                                                    <Upload className="h-3.5 w-3.5" />
                                                    {latest ? 'Upload replacement form' : 'Attach expense form'}
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })()}
                            </div>

                            {/* File Upload Trigger Modal/Box */}
                            {uploadFile && (
                                <div className="rounded-xl border border-indigo-200 bg-indigo-50/70 p-4 space-y-3">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-xs font-bold text-main">
                                                Selected for {uploadType.replace(/_/g, ' ')}:
                                            </p>
                                            <p className="text-xs text-slate-600 font-medium">
                                                {uploadFile.name} ({(uploadFile.size / 1024 / 1024).toFixed(2)} MB)
                                            </p>
                                        </div>
                                        <button
                                            type="button"
                                            className="text-xs font-bold text-slate-500 hover:text-red-600 transition-colors"
                                            onClick={() => setUploadFile(null)}
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                    {uploadProgress !== null && (
                                        <div className="space-y-1">
                                            <div className="flex justify-between text-[10px] text-muted font-semibold">
                                                <span>Uploading to server</span>
                                                <span>{uploadProgress}%</span>
                                            </div>
                                            <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
                                                <div className="h-full bg-indigo-600 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
                                            </div>
                                        </div>
                                    )}
                                    <button
                                        type="button"
                                        className="btn-primary w-full text-xs"
                                        disabled={busy}
                                        onClick={uploadDocument}
                                    >
                                        {busy ? 'Uploading…' : 'Start Secure Upload'}
                                    </button>
                                </div>
                            )}

                            {uploadMessage && (
                                <p className="flex items-center gap-2 text-xs text-teal-800 bg-teal-50 border border-teal-200 p-3 rounded-xl font-medium">
                                    <CheckCircle2 className="h-4 w-4 shrink-0 text-teal-600" />
                                    {uploadMessage}
                                </p>
                            )}

                            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-border pt-4">
                                <span className="text-xs text-muted">
                                    {hasReadyDoc ? '✓ Document ready. Proceed to review extracted figures.' : 'Upload receipt to start extraction.'}
                                </span>
                                <button
                                    type="button"
                                    className="btn-primary"
                                    disabled={!hasReadyDoc}
                                    onClick={() => setWizardStep(2)}
                                >
                                    Continue to Review Extracted Information
                                    <ArrowRight className="h-4 w-4" />
                                </button>
                            </div>
                        </section>
                    )}

                    {/* STEP 2: Review extracted details & fill missing information */}
                    {wizardStep === 2 && (
                        <section className="card p-6 space-y-6">
                            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border pb-3">
                                <div>
                                    <h3 className="text-base font-bold text-main">Step 2 — Review Extracted Information</h3>
                                    <p className="mt-1 text-xs text-muted">
                                        Review the figures detected by OCR. If any required information was not found, enter it below.
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setIsEditingDetails(!isEditingDetails)}
                                    className="btn-secondary text-xs py-1.5 px-3"
                                >
                                    {isEditingDetails ? 'Hide Edit Form' : 'Edit / Correct Details'}
                                </button>
                            </div>

                            {detailsSaveSuccess && (
                                <p className="text-xs text-teal-800 bg-teal-50 border border-teal-200 p-3 rounded-xl font-medium flex items-center gap-2">
                                    <CheckCircle2 className="h-4 w-4 text-teal-600" />
                                    {detailsSaveSuccess}
                                </p>
                            )}

                            {/* Required fields banner: missing vs complete */}
                            {(!request.claimed_amount || !request.expense_date) ? (
                                <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-4 text-xs text-amber-950 space-y-2 shadow-xs">
                                    <p className="font-bold flex items-center gap-2 text-amber-900">
                                        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                                        Additional Required Information Needed
                                    </p>
                                    <p className="text-slate-700 leading-relaxed">
                                        Some required fields could not be automatically detected from your document (e.g. {!request.claimed_amount ? 'claimed amount' : ''}{!request.claimed_amount && !request.expense_date ? ' and ' : ''}{!request.expense_date ? 'expense date' : ''}). Please fill them in below to proceed.
                                    </p>
                                </div>
                            ) : (
                                <div className="rounded-xl border border-teal-200 bg-teal-50/70 p-4 text-xs text-teal-950 space-y-1.5 shadow-xs">
                                    <p className="font-bold flex items-center gap-2 text-teal-900">
                                        <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                                        All Required Expense Details Detected & Ready
                                    </p>
                                    <p className="text-slate-700 leading-relaxed font-medium">
                                        We extracted the amount, date, and merchant. You can proceed directly to verification, or adjust any value using the form below.
                                    </p>
                                </div>
                            )}

                            {/* Prominent Extracted Figures Card */}
                            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs">
                                <div className="rounded-xl border border-surface-border bg-slate-50/80 p-4">
                                    <span className="text-[10px] text-muted block font-bold uppercase tracking-wider">Merchant / Vendor</span>
                                    <span className="text-sm font-bold text-main mt-1 block truncate">
                                        {receiptMerchant || <span className="text-slate-400 font-normal italic">Not detected</span>}
                                    </span>
                                </div>
                                <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-4">
                                    <span className="text-[10px] text-indigo-700 block font-bold uppercase tracking-wider">Claimed Amount</span>
                                    <span className="text-base font-extrabold text-indigo-950 mt-1 block">
                                        {request.claimed_amount != null ? `${request.currency ?? 'INR'} ${Number(request.claimed_amount).toLocaleString()}` : <span className="text-amber-700 font-bold">Needs entry</span>}
                                    </span>
                                </div>
                                <div className="rounded-xl border border-surface-border bg-slate-50/80 p-4">
                                    <span className="text-[10px] text-muted block font-bold uppercase tracking-wider">Expense Date</span>
                                    <span className="text-sm font-bold text-main mt-1 block">
                                        {request.expense_date ? formatExpenseDate(request.expense_date) : <span className="text-amber-700 font-bold">Needs entry</span>}
                                    </span>
                                </div>
                                <div className="rounded-xl border border-surface-border bg-slate-50/80 p-4">
                                    <span className="text-[10px] text-muted block font-bold uppercase tracking-wider">Currency</span>
                                    <span className="text-sm font-bold text-main mt-1 block">
                                        {request.currency || 'INR'}
                                    </span>
                                </div>
                            </div>

                            {/* Inline Edit Form for Missing or Corrected Details */}
                            {(isEditingDetails || !request.claimed_amount || !request.expense_date) && (
                                <form onSubmit={saveClaimDetails} className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-5 space-y-4">
                                    <div className="flex items-center justify-between border-b border-indigo-100 pb-2">
                                        <h4 className="text-xs font-bold text-indigo-950">
                                            {(!request.claimed_amount || !request.expense_date) ? 'Enter Missing Expense Details' : 'Edit Claim Information'}
                                        </h4>
                                        {detailsSaveError && <p className="text-[11px] text-red-600 font-semibold">{detailsSaveError}</p>}
                                    </div>

                                    <div className="grid gap-3 sm:grid-cols-3">
                                        <div>
                                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                Claim Amount ({editCurrency}) <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="number"
                                                step="0.01"
                                                min="0.01"
                                                required
                                                value={editAmount}
                                                onChange={(e) => setEditAmount(e.target.value)}
                                                placeholder="e.g. 450.00"
                                                className="form-input text-xs py-1.5 w-full"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                Expense Date <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="date"
                                                required
                                                value={editDate}
                                                onChange={(e) => setEditDate(e.target.value)}
                                                className="form-input text-xs py-1.5 w-full"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                Category
                                            </label>
                                            <select
                                                value={editCategory}
                                                onChange={(e) => setEditCategory(e.target.value)}
                                                className="form-input text-xs py-1.5 w-full"
                                            >
                                                <option value="travel">Travel</option>
                                                <option value="meals">Meals & Dining</option>
                                                <option value="lodging">Lodging & Hotel</option>
                                                <option value="supplies">Office Supplies</option>
                                                <option value="software">Software & Tech</option>
                                                <option value="other">Other</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div className="grid gap-3 sm:grid-cols-2">
                                        <div>
                                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                Claim Title
                                            </label>
                                            <input
                                                type="text"
                                                value={editTitle}
                                                onChange={(e) => setEditTitle(e.target.value)}
                                                placeholder="e.g. Starbucks Reimbursement"
                                                className="form-input text-xs py-1.5 w-full"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                Purpose / Description (Optional)
                                            </label>
                                            <input
                                                type="text"
                                                value={editDescription}
                                                onChange={(e) => setEditDescription(e.target.value)}
                                                placeholder="e.g. Client coffee meeting"
                                                className="form-input text-xs py-1.5 w-full"
                                            />
                                        </div>
                                    </div>

                                    <div className="flex justify-end gap-2 pt-1">
                                        <button
                                            type="submit"
                                            disabled={savingDetails || !editAmount || !editDate}
                                            className="btn-primary text-xs py-1.5 px-4 font-bold"
                                        >
                                            {savingDetails ? 'Saving…' : 'Save Details'}
                                        </button>
                                    </div>
                                </form>
                            )}

                            {/* Assignee Routing & Reviewer Assignment Card */}
                            <div className="rounded-xl border border-surface-border bg-slate-50/70 p-4 space-y-3">
                                <div className="flex items-center justify-between">
                                    <h4 className="text-xs font-bold text-main uppercase tracking-wider">Approval Routing</h4>
                                    {!isEditingAssignees && isSubmitter && (
                                        <button
                                            type="button"
                                            onClick={startEditingAssignees}
                                            className="text-[11px] font-bold text-indigo-700 hover:underline"
                                        >
                                            Change Assignees
                                        </button>
                                    )}
                                </div>

                                {isEditingAssignees ? (
                                    <div className="space-y-3 pt-2">
                                        {assigneeSaveError && <p className="text-[11px] text-red-600 font-semibold">{assigneeSaveError}</p>}
                                        <div className="grid gap-3 sm:grid-cols-2">
                                            <div>
                                                <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                    Assigned Reviewer
                                                </label>
                                                <select
                                                    value={selectedReviewerId}
                                                    onChange={(e) => setSelectedReviewerId(e.target.value)}
                                                    className="form-input text-xs py-1.5"
                                                    disabled={assigneeSaving}
                                                >
                                                    <option value="">Select a reviewer</option>
                                                    {assigneeList.filter((a) => a.role === 'reviewer').map((rev) => (
                                                        <option key={rev.id} value={rev.id}>
                                                            {rev.display_name}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>
                                            <div>
                                                <label className="text-[10px] font-bold uppercase tracking-wider text-muted block mb-1">
                                                    Human Approver
                                                </label>
                                                <select
                                                    value={selectedApproverId}
                                                    onChange={(e) => setSelectedApproverId(e.target.value)}
                                                    className="form-input text-xs py-1.5"
                                                    disabled={assigneeSaving}
                                                >
                                                    <option value="">Select an approver</option>
                                                    {assigneeList.filter((a) => a.role === 'approver').map((app) => (
                                                        <option key={app.id} value={app.id}>
                                                            {app.display_name}
                                                        </option>
                                                    ))}
                                                </select>
                                            </div>
                                        </div>
                                        <div className="flex justify-end gap-2 pt-1">
                                            <button
                                                type="button"
                                                onClick={() => setIsEditingAssignees(false)}
                                                className="btn-secondary text-xs py-1 px-3"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                type="button"
                                                onClick={saveAssignees}
                                                disabled={assigneeSaving}
                                                className="btn-primary text-xs py-1 px-3"
                                            >
                                                {assigneeSaving ? 'Saving…' : 'Save Assignees'}
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="grid gap-3 sm:grid-cols-2 text-xs">
                                        <div>
                                            <span className="text-muted block text-[10px]">Reviewer:</span>
                                            <strong className="text-main font-bold">{request.assigned_reviewer?.display_name ?? 'Not assigned'}</strong>
                                        </div>
                                        <div>
                                            <span className="text-muted block text-[10px]">Approver:</span>
                                            <strong className="text-main font-bold">{request.assigned_approver?.display_name ?? 'Not assigned'}</strong>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-border pt-4">
                                <button
                                    type="button"
                                    className="btn-secondary"
                                    onClick={() => setWizardStep(1)}
                                >
                                    ← Back: Documents
                                </button>
                                <button
                                    type="button"
                                    className="btn-primary"
                                    disabled={!request.claimed_amount || !request.expense_date}
                                    onClick={() => setWizardStep(3)}
                                >
                                    Continue to Verification
                                    <ArrowRight className="h-4 w-4" />
                                </button>
                            </div>
                        </section>
                    )}

                    {/* STEP 3: Automated document verification & comparison */}
                    {wizardStep === 3 && (
                        <section className="space-y-6">
                            {/* Plain-Language Status Alert */}
                            {amountMismatchCheck && amountMismatchCheck.result === 'flag' && amountMismatchCheck.resolution_status === 'open' ? (
                                <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-4 text-xs text-amber-950 space-y-1.5 shadow-xs">
                                    <div className="flex items-center gap-2 font-bold text-amber-900">
                                        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                                        <span>Amount difference detected between documents.</span>
                                    </div>
                                    <p className="leading-relaxed text-slate-700">
                                        {amountMismatchCheck.explanation}
                                    </p>
                                    <p className="text-slate-800 font-semibold pt-1">
                                        <strong>Note:</strong> A mismatch requires reviewer verification. It does not mean your claim is rejected. You can return to Step 1 or Step 2 to make adjustments if needed.
                                    </p>
                                </div>
                            ) : missingFieldCheck && missingFieldCheck.result === 'flag' && missingFieldCheck.resolution_status === 'open' ? (
                                <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-4 text-xs text-amber-950 space-y-1.5 shadow-xs">
                                    <div className="flex items-center gap-2 font-bold text-amber-900">
                                        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                                        <span>Some document fields could not be confidently read.</span>
                                    </div>
                                    <p className="leading-relaxed text-slate-700">
                                        {missingFieldCheck.explanation}
                                    </p>
                                    <p className="text-slate-800 font-semibold pt-1">
                                        <strong>Note:</strong> A human reviewer will inspect the uploaded document to verify these details.
                                    </p>
                                </div>
                            ) : (
                                <div className="rounded-xl border border-teal-200 bg-teal-50/70 p-4 text-xs text-teal-950 shadow-xs">
                                    <div className="flex items-center gap-2 font-bold text-teal-900">
                                        <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                                        <span>Automated verification complete. All readable information verified.</span>
                                    </div>
                                    <p className="mt-1 text-slate-700 font-medium">
                                        Review the verification summary below and proceed to Step 4 to submit.
                                    </p>
                                </div>
                            )}

                            {/* Clean Document Summary Card */}
                            <div className="card overflow-hidden border-indigo-200/70 shadow-md">
                                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border bg-slate-50/80 px-6 py-4">
                                    <div className="flex items-center gap-2.5">
                                        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-xs">
                                            <Receipt className="h-4 w-4" />
                                        </span>
                                        <div>
                                            <h3 className="text-sm font-bold text-main">Receipt Information</h3>
                                            <p className="text-[10px] text-muted">Summary of extracted receipt data</p>
                                        </div>
                                    </div>
                                    {latestReceipt && (
                                        <span className="rounded-md bg-white px-2.5 py-1 text-[10px] font-bold text-slate-700 ring-1 ring-surface-border shadow-xs">
                                            Receipt v{latestReceipt.version_number}
                                        </span>
                                    )}
                                </div>
                                <div className="p-6">
                                    <div className="space-y-4">
                                        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-surface-border pb-4">
                                            <div>
                                                <h4 className="text-2xl font-black text-main sm:text-3xl">
                                                    {receiptMerchant || <span className="text-sm font-normal italic text-slate-400">Merchant not detected</span>}
                                                </h4>
                                                <p className="mt-1 text-sm font-bold text-muted">
                                                    {receiptDateFormatted || <span className="text-xs font-normal italic text-slate-400">Date not detected</span>}
                                                </p>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-3xl font-black text-indigo-950 sm:text-4xl">
                                                    {receiptAmountFormatted || <span className="text-sm font-normal italic text-slate-400">Amount not detected</span>}
                                                </p>
                                            </div>
                                        </div>
                                        {receiptReference && (
                                            <p className="text-xs text-slate-700 font-medium">
                                                Reference / Invoice #: <strong className="text-main">{receiptReference}</strong>
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Comparison Side-by-Side if expense form is uploaded */}
                            {latestExpenseForm && (
                                <div className="card p-5">
                                    <h4 className="text-xs font-bold text-main mb-3">Expense Form Comparison</h4>
                                    <div className="grid gap-3 sm:grid-cols-3 text-xs">
                                        <div className="rounded-xl border border-surface-border bg-slate-50/80 p-3">
                                            <span className="text-[10px] text-muted block font-bold uppercase tracking-wider">Employee Name</span>
                                            <span className="font-bold text-main mt-0.5 block">{formEmployeeEff.value || 'Not detected'}</span>
                                        </div>
                                        <div className="rounded-xl border border-surface-border bg-slate-50/80 p-3">
                                            <span className="text-[10px] text-muted block font-bold uppercase tracking-wider">Form Amount</span>
                                            <span className="font-bold text-main mt-0.5 block">
                                                {formAmountEff.value ? formatReceiptAmount(formAmountEff.value, request.currency ?? 'INR') : 'Not detected'}
                                            </span>
                                        </div>
                                        <div className="rounded-xl border border-surface-border bg-slate-50/80 p-3">
                                            <span className="text-[10px] text-muted block font-bold uppercase tracking-wider">Form Date</span>
                                            <span className="font-bold text-main mt-0.5 block">
                                                {formDateEff.value ? formatExpenseDate(formDateEff.value) : 'Not detected'}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Document Preview */}
                            {selectedDocument && previewUrl && (
                                <div className="card p-5">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="text-xs font-bold text-main">Visual Preview: {selectedDocument.original_filename}</h4>
                                        <a href={previewUrl} download={selectedDocument.original_filename} className="btn-secondary text-[11px] py-1.5 px-3">
                                            <Download className="h-3 w-3" /> Download
                                        </a>
                                    </div>
                                    <div className="max-h-[380px] overflow-auto rounded-xl border border-surface-border bg-slate-50 flex items-center justify-center p-2">
                                        {selectedDocument.mime_type?.startsWith('image/') ? (
                                            <img src={previewUrl} alt="Preview" className="max-h-[360px] object-contain rounded-lg shadow-xs" />
                                        ) : (
                                            <iframe src={previewUrl} title="Document Preview" className="h-[360px] w-full rounded-lg" />
                                        )}
                                    </div>
                                </div>
                            )}

                            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-border pt-4">
                                <button
                                    type="button"
                                    className="btn-secondary"
                                    onClick={() => setWizardStep(2)}
                                >
                                    ← Back: Extracted Details
                                </button>
                                <button
                                    type="button"
                                    className="btn-primary"
                                    onClick={() => setWizardStep(4)}
                                >
                                    Continue to Submit
                                    <ArrowRight className="h-4 w-4" />
                                </button>
                            </div>
                        </section>
                    )}

                    {/* STEP 4: Review and submit */}
                    {wizardStep === 4 && (
                        <section className="card p-6 space-y-6">
                            <div className="border-b border-surface-border pb-3">
                                <h3 className="text-base font-bold text-main">Step 4 — Review and submit</h3>
                                <p className="mt-1 text-xs text-muted">
                                    Confirm the claim details and submit for reviewer evaluation and executive sign-off.
                                </p>
                            </div>

                            {/* Claim Summary */}
                            <div className="rounded-xl border border-surface-border bg-slate-50/70 p-4 space-y-3">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-muted">Claim Summary</h4>
                                <dl className="grid gap-2 sm:grid-cols-2 text-xs">
                                    <div><span className="text-muted">Claim Number:</span> <strong className="text-main ml-1">{request.request_number}</strong></div>
                                    <div><span className="text-muted">Claim Title:</span> <strong className="text-main ml-1">{request.title}</strong></div>
                                    <div><span className="text-muted">Total Claimed:</span> <strong className="text-indigo-950 font-bold ml-1">{request.currency ?? 'INR'} {Number(request.claimed_amount ?? 0).toLocaleString()}</strong></div>
                                    <div><span className="text-muted">Expense Date:</span> <strong className="text-main ml-1">{request.expense_date ? formatExpenseDate(request.expense_date) : '—'}</strong></div>
                                    <div><span className="text-muted">Assigned Reviewer:</span> <strong className="text-main ml-1">{request.assigned_reviewer?.display_name ?? '—'}</strong></div>
                                    <div><span className="text-muted">Human Approver:</span> <strong className="text-main ml-1">{request.assigned_approver?.display_name ?? '—'}</strong></div>
                                </dl>
                            </div>

                            {/* Pre-Submission Checklist */}
                            <div className="space-y-3">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-muted">Submission Checklist</h4>
                                <div className="space-y-2 text-xs">
                                    <div className="flex items-center gap-2.5">
                                        <span className={latestReceipt?.processing_status === 'ready' || latestExpenseForm?.processing_status === 'ready' ? 'flex h-5 w-5 items-center justify-center rounded-full bg-teal-100 text-teal-700 font-bold text-[11px]' : 'flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 text-slate-400 font-bold text-[11px]'}>
                                            {latestReceipt?.processing_status === 'ready' || latestExpenseForm?.processing_status === 'ready' ? '✓' : '○'}
                                        </span>
                                        <span className={latestReceipt?.processing_status === 'ready' || latestExpenseForm?.processing_status === 'ready' ? 'text-main font-semibold' : 'text-muted'}>
                                            Expense document verified & extracted
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2.5">
                                        <span className={request.claimed_amount != null && request.expense_date ? 'flex h-5 w-5 items-center justify-center rounded-full bg-teal-100 text-teal-700 font-bold text-[11px]' : 'flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 text-slate-400 font-bold text-[11px]'}>
                                            {request.claimed_amount != null && request.expense_date ? '✓' : '○'}
                                        </span>
                                        <span className={request.claimed_amount != null && request.expense_date ? 'text-main font-semibold' : 'text-muted'}>
                                            Expense amount ({request.currency ?? 'INR'} {request.claimed_amount}) and date confirmed
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2.5">
                                        <span className={request.assigned_reviewer_id && request.assigned_approver_id ? 'flex h-5 w-5 items-center justify-center rounded-full bg-teal-100 text-teal-700 font-bold text-[11px]' : 'flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 text-slate-400 font-bold text-[11px]'}>
                                            {request.assigned_reviewer_id && request.assigned_approver_id ? '✓' : '○'}
                                        </span>
                                        <span className={request.assigned_reviewer_id && request.assigned_approver_id ? 'text-main font-semibold' : 'text-muted'}>
                                            Active reviewer and approver designated
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Submission Readiness Alert */}
                            {submissionBlockReason ? (
                                <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-950 space-y-1.5 shadow-xs">
                                    <p className="font-bold flex items-center gap-2 text-amber-900">
                                        <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                                        Submission requirement pending:
                                    </p>
                                    <p className="text-slate-700 font-medium pl-6">{submissionBlockReason}</p>
                                </div>
                            ) : (
                                <div className="rounded-xl border border-teal-200 bg-teal-50/70 p-4 text-xs text-teal-950 space-y-1.5 shadow-xs">
                                    <p className="font-bold flex items-center gap-2 text-teal-900">
                                        <CheckCircle2 className="h-4 w-4 text-teal-600 shrink-0" />
                                        All requirements met. Ready to submit for review.
                                    </p>
                                    <p className="text-slate-700 leading-relaxed font-medium pl-6">
                                        When you select Submit Claim, your claim is sent to your assigned reviewer ({request.assigned_reviewer?.display_name}). You can track its progress through human review and final approval.
                                    </p>
                                </div>
                            )}

                            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-surface-border pt-4">
                                <button
                                    type="button"
                                    className="btn-secondary"
                                    onClick={() => setWizardStep(3)}
                                >
                                    ← Back: Verification
                                </button>
                                <button
                                    type="button"
                                    className="btn-primary"
                                    disabled={busy || Boolean(submissionBlockReason)}
                                    onClick={submitDraft}
                                >
                                    {busy ? (
                                        'Submitting claim…'
                                    ) : (
                                        <>
                                            <Send className="h-4 w-4" />
                                            Submit claim for review
                                        </>
                                    )}
                                </button>
                            </div>
                        </section>
                    )}
"""
    content = content[:start_idx] + new_wizard + content[end_idx:]
    path.write_text(content, encoding="utf-8")
    print("Replaced draft wizard block successfully.")
else:
    print(f"Could not locate start ({start_idx}) or end ({end_idx})")
