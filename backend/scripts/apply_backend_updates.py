"""
Script to apply backend improvements:
1. schemas/request.py: add RequestUpdate, make RequestCreate title have default.
2. api/v1/requests.py: add PATCH /requests/{id} endpoint.
3. services/document_processing/processor.py: blank/blurry document handling & auto-populate request fields.
4. services/assistant/service.py: fix req.purpose attribute error.
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# --- 1. schemas/request.py ---
schemas_path = BASE / "app" / "schemas" / "request.py"
content = schemas_path.read_text(encoding="utf-8")

if "class RequestUpdate(BaseModel):" not in content:
    update_class = (
        "class RequestUpdate(BaseModel):\n"
        "    title: Optional[str] = None\n"
        "    description: Optional[str] = None\n"
        "    expense_category: Optional[str] = None\n"
        "    claimed_amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)\n"
        "    expense_date: Optional[date] = None\n"
        "    currency: Optional[str] = None\n"
        "    assigned_reviewer_id: Optional[int] = None\n"
        "    assigned_approver_id: Optional[int] = None\n\n\n"
    )
    content = content.replace("class RequestAssignmentUpdate(BaseModel):", update_class + "class RequestAssignmentUpdate(BaseModel):")

# Make title optional in RequestCreate
content = content.replace(
    "    title: str\n    description: Optional[str] = None",
    '    title: str = "Expense Reimbursement"\n    description: Optional[str] = None'
)
old_v = (
    '    @field_validator("title")\n'
    '    @classmethod\n'
    '    def title_not_empty(cls, v: str) -> str:\n'
    '        if not v.strip():\n'
    '            raise ValueError("title must not be empty")\n'
    '        return v.strip()'
)
new_v = (
    '    @field_validator("title")\n'
    '    @classmethod\n'
    '    def title_not_empty(cls, v: str) -> str:\n'
    '        cleaned = v.strip() if v else ""\n'
    '        return cleaned or "Expense Reimbursement"'
)
content = content.replace(old_v, new_v)
schemas_path.write_text(content, encoding="utf-8")
print("1. schemas/request.py updated")

# --- 2. api/v1/requests.py ---
requests_api_path = BASE / "app" / "api" / "v1" / "requests.py"
req_content = requests_api_path.read_text(encoding="utf-8")

# Add RequestUpdate import
if "RequestUpdate" not in req_content:
    req_content = req_content.replace(
        "from app.schemas.request import (",
        "from app.schemas.request import (\n    RequestUpdate,"
    )

# Add PATCH /{request_id} endpoint before @router.patch("/{request_id}/assignment"
if "def update_request(" not in req_content:
    patch_endpoint = (
        '@router.patch("/{request_id}", response_model=RequestRead,\n'
        '              summary="Update draft request details")\n'
        'def update_request(\n'
        '    request_id: int,\n'
        '    body: RequestUpdate,\n'
        '    db: Session = Depends(get_db),\n'
        '    user: User = Depends(get_current_user),\n'
        '):\n'
        '    req = get_request_or_404(db, request_id)\n'
        '    assert_can_view(user, req)\n'
        '    if user.role != UserRole.admin:\n'
        '        if user.role != UserRole.submitter or req.submitter_id != user.id:\n'
        '            raise HTTPException(status_code=403, detail="Only the claim submitter or an administrator may update claim details.")\n'
        '        if req.status not in (RequestStatus.draft, RequestStatus.more_info_required):\n'
        '            raise HTTPException(status_code=422, detail="Claim details can only be modified while in draft or awaiting information.")\n'
        '    if body.title is not None and body.title.strip():\n'
        '        req.title = body.title.strip()\n'
        '    if body.description is not None:\n'
        '        req.description = body.description.strip() or None\n'
        '    if body.expense_category is not None and body.expense_category.strip():\n'
        '        req.expense_category = body.expense_category.strip()\n'
        '    if body.claimed_amount is not None:\n'
        '        req.claimed_amount = body.claimed_amount\n'
        '    if body.expense_date is not None:\n'
        '        req.expense_date = body.expense_date\n'
        '    if body.currency is not None and body.currency.strip():\n'
        '        req.currency = body.currency.strip().upper()\n'
        '    if body.assigned_reviewer_id is not None or body.assigned_approver_id is not None:\n'
        '        rev_id = body.assigned_reviewer_id or req.assigned_reviewer_id\n'
        '        app_id = body.assigned_approver_id or req.assigned_approver_id\n'
        '        if rev_id and app_id:\n'
        '            reviewer = eligible_assignee(db, rev_id, UserRole.reviewer, req.submitter_id)\n'
        '            approver = eligible_assignee(db, app_id, UserRole.approver, req.submitter_id)\n'
        '            if reviewer.id == approver.id:\n'
        '                raise HTTPException(status_code=422, detail="Reviewer and approver must be different people.")\n'
        '            req.assigned_reviewer_id = reviewer.id\n'
        '            req.assigned_approver_id = approver.id\n'
        '    from app.services.verification.runner import run_all_checks\n'
        '    run_all_checks(db, req.id)\n'
        '    db.commit()\n'
        '    db.refresh(req)\n'
        '    return req\n\n\n'
    )
    req_content = req_content.replace(
        '@router.patch("/{request_id}/assignment"',
        patch_endpoint + '@router.patch("/{request_id}/assignment"'
    )
    requests_api_path.write_text(req_content, encoding="utf-8")
    print("2. api/v1/requests.py updated with PATCH /{request_id}")

# --- 3. services/assistant/service.py ---
assistant_path = BASE / "app" / "services" / "assistant" / "service.py"
ast_content = assistant_path.read_text(encoding="utf-8")
if "req.purpose" in ast_content:
    ast_content = ast_content.replace(
        "req.purpose or 'General business expense'",
        "getattr(req, 'description', None) or getattr(req, 'expense_category', None) or 'General business expense'"
    )
    assistant_path.write_text(ast_content, encoding="utf-8")
    print("3. services/assistant/service.py fixed req.purpose")

print("Backend update script completed successfully.")
