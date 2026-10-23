"""Phase 1 verification: check DB tables exist and app imports cleanly."""
import sqlite3
import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, ".")

# 1. Check DB tables
conn = sqlite3.connect("docuverify.db")
tables = sorted([row[0] for row in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()])
conn.close()

EXPECTED_APP = sorted([
    "users", "requests", "document_versions", "extraction_runs",
    "extracted_fields", "reviewer_corrections", "verification_checks",
    "review_actions", "audit_events",
])

print("=== DATABASE TABLES ===")
for t in tables:
    marker = "OK" if (t in EXPECTED_APP or t == "alembic_version") else "UNKNOWN"
    print(f"  [{marker}] {t}")

missing = set(EXPECTED_APP) - set(tables)
if missing:
    print(f"\nMISSING TABLES: {missing}")
    sys.exit(1)
else:
    print(f"\nAll {len(set(EXPECTED_APP))} application tables present.")

# 2. Check FastAPI app imports
print("\n=== APP IMPORTS ===")
try:
    from main import app
    print(f"  [OK] FastAPI app imported: {app.title} v{app.version}")
except Exception as e:
    print(f"  [FAIL] Import failed: {e}")
    sys.exit(1)

# 3. Check all model imports
print("\n=== MODEL IMPORTS ===")
try:
    import app.models as models
    expected_models = [
        "User", "Request", "DocumentVersion", "ExtractionRun",
        "ExtractedField", "ReviewerCorrection", "VerificationCheck",
        "ReviewAction", "AuditEvent",
    ]
    all_ok = True
    for m in expected_models:
        obj = getattr(models, m, None)
        if obj:
            print(f"  [OK] {m}")
        else:
            print(f"  [FAIL] {m} MISSING")
            all_ok = False
    if not all_ok:
        sys.exit(1)
except Exception as e:
    print(f"  [FAIL] Import failed: {e}")
    sys.exit(1)

print("\nPhase 1 pre-flight: ALL CHECKS PASSED")
