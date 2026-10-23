import re
from pathlib import Path

path = Path("frontend/src/pages/RequestDetailPage.tsx")
content = path.read_text(encoding="utf-8")

# 1. Add state for editing claim details if not present
if "const [isEditingDetails, setIsEditingDetails]" not in content:
    state_injection = """    // Claim details editing & missing fields input
    const [isEditingDetails, setIsEditingDetails] = useState(false);
    const [editAmount, setEditAmount] = useState('');
    const [editDate, setEditDate] = useState('');
    const [editTitle, setEditTitle] = useState('');
    const [editCategory, setEditCategory] = useState('travel');
    const [editCurrency, setEditCurrency] = useState('INR');
    const [editDescription, setEditDescription] = useState('');
    const [savingDetails, setSavingDetails] = useState(false);
    const [detailsSaveError, setDetailsSaveError] = useState<string | null>(null);
    const [detailsSaveSuccess, setDetailsSaveSuccess] = useState<string | null>(null);
"""
    content = content.replace("    const [isEditingAssignees, setIsEditingAssignees] = useState(false);", state_injection + "    const [isEditingAssignees, setIsEditingAssignees] = useState(false);")

# 2. Add saveClaimDetails function if not present
if "async function saveClaimDetails(" not in content:
    fn_injection = """    async function saveClaimDetails(e?: React.FormEvent) {
        if (e) e.preventDefault();
        setSavingDetails(true);
        setDetailsSaveError(null);
        setDetailsSaveSuccess(null);
        try {
            await api.patch(`/requests/${recordId}`, {
                title: editTitle.trim() || undefined,
                claimed_amount: editAmount ? editAmount : undefined,
                expense_date: editDate || undefined,
                expense_category: editCategory || undefined,
                currency: editCurrency || undefined,
                description: editDescription.trim() || undefined,
            });
            setDetailsSaveSuccess('Claim details updated and verification checks refreshed.');
            setIsEditingDetails(false);
            await load(true);
        } catch (err: unknown) {
            const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
            setDetailsSaveError(typeof msg === 'string' ? msg : 'Failed to update claim details.');
        } finally {
            setSavingDetails(false);
        }
    }
"""
    content = content.replace("    async function saveAssignees() {", fn_injection + "    async function saveAssignees() {")

# 3. Synchronize edit states when request loads
if "setEditAmount(reqRes.data.claimed_amount" not in content:
    sync_code = """            setRequest(reqRes.data);
            if (reqRes.data.claimed_amount != null) setEditAmount(String(reqRes.data.claimed_amount));
            if (reqRes.data.expense_date) setEditDate(reqRes.data.expense_date);
            if (reqRes.data.title) setEditTitle(reqRes.data.title);
            if (reqRes.data.expense_category) setEditCategory(reqRes.data.expense_category);
            if (reqRes.data.currency) setEditCurrency(reqRes.data.currency);
            if (reqRes.data.description) setEditDescription(reqRes.data.description);"""
    content = content.replace("            setRequest(reqRes.data);", sync_code)

path.write_text(content, encoding="utf-8")
print("1. Added detail editing state & sync functions to RequestDetailPage.tsx")
